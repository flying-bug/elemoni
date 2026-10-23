"""Controlled synthetic detective pairs, oracle and caller-supplied NILM comparison."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd

from src.detective.duty_cycle import FridgeDutyCycleAnalyzer
from src.detective.rule_engine import DeterministicRuleEngine
from src.detective.vampire_power import VampirePowerDetector
from .synthetic_households import ROOT, EPOCH, find_omc, run_command, sha256, write_json


def confusion(decisions: list[tuple[bool, bool | None]]) -> dict[str, Any]:
    counts = dict(tp=0,fp=0,tn=0,fn=0,not_evaluated=0)
    for truth,pred in decisions:
        if pred is None:
            counts['not_evaluated'] += 1
        else:
            counts[('tp' if truth else 'fp') if pred else ('fn' if truth else 'tn')] += 1
    tp,fp,tn,fn = (counts[k] for k in ('tp','fp','tn','fn'))
    return {**counts,'precision':tp/(tp+fp) if tp+fp else None,
            'recall':tp/(tp+fn) if tp+fn else None,
            'false_positive_rate':fp/(fp+tn) if fp+tn else None,
            'false_negative_rate':fn/(fn+tp) if fn+tp else None,
            'unit':'scenario case, not events'}


def validate_frame(frame: pd.DataFrame, appliance_bound: bool = True) -> None:
    try:
        values=frame[['Unix','Aggregate','Fridge','Kettle']].to_numpy(dtype=float)
    except (KeyError,ValueError,TypeError) as exc:
        raise ValueError('Expected numeric Unix,Aggregate,Fridge,Kettle') from exc
    if len(values)<2 or not np.isfinite(values).all() or (values<0).any():
        raise ValueError('Invalid diagnostic values')
    delta=np.diff(values[:,0])
    if delta[0] not in (1,8) or not np.allclose(delta,delta[0],atol=0,rtol=0):
        raise ValueError('Diagnostic input must be contiguous at 1 or 8 seconds')
    if appliance_bound and (values[:,2:] > values[:,1,None]+1e-6).any():
        raise ValueError('Appliance exceeds aggregate')


def detect(detector: str, frame: pd.DataFrame, predicted: bool = False) -> dict[str, Any]:
    validate_frame(frame,appliance_bound=not predicted)
    local=pd.to_datetime(frame.Unix,unit='s',utc=True).dt.tz_convert('Asia/Ho_Chi_Minh').dt.tz_localize(None)
    if detector=='fridge':
        cycles=FridgeDutyCycleAnalyzer().extract_cycles(
            pd.DataFrame({'power_smoothed':frame.Fridge.to_numpy()},index=pd.DatetimeIndex(local)))
        return {'positive':any(c.is_anomaly for c in cycles) if cycles else None,
                'cycle_count':len(cycles),'cycles':[{'start':str(c.start_time),
                    'duty_cycle_pct':c.duty_cycle_pct,'positive':bool(c.is_anomaly)} for c in cycles]}
    if detector=='standby':
        report=VampirePowerDetector().analyze_night_standby(
            pd.DataFrame({'timestamp':local,'total_power':frame.Aggregate.to_numpy()}))
        return {'positive':bool(report.is_anomaly) if report else None,
                'standby_w':report.standby_power_watts if report else None}
    query={'kettle':24360,'pulse':43260}.get(detector)
    if query is None:
        raise ValueError('Unknown detector')
    mask=frame.Unix<=EPOCH+query
    if not mask.any() or frame.Unix.max()<EPOCH+query-7:
        return {'positive':None,'reason':'query not covered'}
    engine=DeterministicRuleEngine()
    series=frame.loc[mask,'Kettle' if detector=='kettle' else 'Aggregate'].reset_index(drop=True)
    times=local.loc[mask].reset_index(drop=True)
    if detector=='pulse':
        if frame.Unix.diff().dropna().iloc[0] != 1:
            raise ValueError('Pulse benchmark requires 1-second aggregate')
        alert=engine.check_micro_arc_and_spikes(series,times)
    else:
        alert=engine.check_forgotten_appliance('kettle',series,times)
    return {'positive':alert is not None,'query_local':str(times.iloc[-1]),
            'alert_type':alert.alert_type if alert else None}


def compare_predictions(cases: list[dict[str,Any]], frames: dict[str,pd.DataFrame],
                        predictions: Path | None, provenance: dict[str,Any] | None) -> dict[str,Any]:
    eligible={c['case_id']:c for c in cases if c['detector'] in ('fridge','kettle')}
    supplied: dict[str,pd.DataFrame]={}
    if predictions is not None:
        meta=provenance or {}
        if (meta.get('kind')!='nilm_checkpoint' or meta.get('sample_seconds')!=8
            or meta.get('appliance') not in ('Fridge','Kettle')
            or not re.fullmatch('[0-9a-fA-F]{64}',str(meta.get('checkpoint_sha256','')))):
            raise ValueError('Explicit checkpoint provenance, appliance and cadence required')
        pred=pd.read_csv(predictions)
        if not {'case_id','Unix','predicted_w'}<=set(pred.columns):
            raise ValueError('Missing prediction columns')
        numeric=pred[['Unix','predicted_w']].to_numpy(dtype=float)
        if not np.isfinite(numeric).all() or (numeric<0).any():
            raise ValueError('Invalid predictions')
        for case_id,group in pred.groupby('case_id',dropna=False):
            if case_id not in eligible or eligible[case_id]['detector'].capitalize()!=meta['appliance']:
                raise ValueError('Unknown or mismatched target prediction case')
            supplied[str(case_id)]=group
    results=[]
    decisions=[]
    flips={'lost_positive':0,'gained_positive':0,'lost_evidence':0}
    positive_without_alert=0
    for case_id,case in eligible.items():
        if case_id not in supplied:
            results.append({'case_id':case_id,'status':'not_evaluated'})
            decisions.append((case['expected_positive'],None))
            continue
        frame=frames[case_id]
        validate_frame(frame)
        if len(frame)%8 or not np.array_equal(frame.Unix.to_numpy(),EPOCH+np.arange(len(frame))):
            raise ValueError('Expected complete native case for alignment')
        columns=['Aggregate','Fridge','Kettle']
        power=frame[columns].to_numpy().reshape(-1,8,3).mean(axis=1)
        aligned=pd.DataFrame(power,columns=columns)
        aligned['Unix']=EPOCH+np.arange(len(aligned))*8
        aligned=aligned.iloc[29:-29].reset_index(drop=True)
        group=supplied[case_id]
        if len(aligned)<2 or not np.array_equal(group.Unix.to_numpy(),aligned.Unix.to_numpy()):
            raise ValueError('Prediction times must exactly match full-window interior grid')
        baseline=detect(case['detector'],aligned)['positive']
        inferred=aligned.copy()
        target=case['detector'].capitalize()
        inferred[target]=group.predicted_w.to_numpy()
        above_total=int((inferred[target]>inferred.Aggregate+1e-6).sum())
        predicted=detect(case['detector'],inferred,predicted=True)['positive']
        decisions.append((case['expected_positive'],predicted))
        if baseline is True and predicted is False: flips['lost_positive']+=1
        if baseline is False and predicted is True: flips['gained_positive']+=1
        if baseline is not None and predicted is None: flips['lost_evidence']+=1
        if case['expected_positive'] and predicted is not True: positive_without_alert+=1
        results.append({'case_id':case_id,'status':'evaluated','aligned_oracle_positive':baseline,
                        'predicted_positive':predicted,'samples':len(aligned),
                        'prediction_above_aggregate_samples':above_total})
    return {'status':'evaluated' if supplied else 'not_evaluated','metrics':confusion(decisions),
            'decision_flips':flips if supplied else None,'cases':results,
            'positive_cases_without_alert':positive_without_alert if supplied else None,
            'not_applicable':['standby','pulse'],
            'provenance':provenance if predictions is not None else None,
            'note':'Prediction provenance is caller-attributed, not independently verified inference.'}


def infer_checkpoint(benchmark: Path, checkpoint: Path, output: Path,
                     allow_domain_shift: bool = False, threads: int = 4) -> dict[str,Any]:
    """Run explicit frozen weights on paired aggregate; never train or select weights."""
    import torch
    from .seq2point import Seq2PointCNN, predict_appliance_power
    if output.exists(): raise FileExistsError(output)
    if isinstance(threads,bool) or not isinstance(threads,int) or threads<1:
        raise ValueError('Positive integer threads required')
    state=torch.load(checkpoint,map_location='cpu',weights_only=True)
    appliance=state.get('appliance')
    domain_shift=appliance=='fridge_freezer'
    if domain_shift and not allow_domain_shift:
        raise ValueError('Explicit allow-domain-shift required for fridge_freezer vs synthetic fridge')
    if appliance not in ('synthetic_fridge','fridge_freezer','kettle'):
        raise ValueError('Unsupported checkpoint target')
    if state.get('sample_seconds')!=8 or state.get('window_size')!=59:
        raise ValueError('Checkpoint requires cadence 8 and window 59')
    stats=state.get('normalization',{})
    keys=('agg_mean','agg_std','app_mean','app_std')
    if any(not isinstance(stats.get(k),(int,float)) or not np.isfinite(stats[k]) for k in keys):
        raise ValueError('Invalid normalization')
    if stats['agg_std']<=0 or stats['app_std']<=0: raise ValueError('Invalid normalization std')
    model=Seq2PointCNN(59)
    model.load_state_dict(state['model_state'])
    if not all(torch.isfinite(v).all() for v in model.state_dict().values()):
        raise ValueError('Nonfinite checkpoint weights')
    source_report=json.loads((benchmark/'report.json').read_text(encoding='utf-8'))
    target='Kettle' if appliance=='kettle' else 'Fridge'
    cases=source_report['cases']
    selected=[c for c in cases if c['detector'].capitalize()==target]
    if not selected: raise ValueError('No matching benchmark cases')
    frames={}
    for case in selected:
        path=benchmark/case['csv']
        if sha256(path)!=case['csv_sha256']: raise ValueError('Benchmark case hash mismatch')
        frame=pd.read_csv(path)
        validate_frame(frame)
        if len(frame)%8 or not np.array_equal(frame.Unix.to_numpy(),EPOCH+np.arange(len(frame))):
            raise ValueError('Invalid native grid')
        if len(frame)//8<61: raise ValueError('Insufficient full-window support')
        frames[case['case_id']]=frame
    output=output.resolve()
    output.mkdir(parents=True)
    write_json(output/'status.json',{'state':'running'})
    previous_threads=torch.get_num_threads()
    try:
        torch.set_num_threads(threads)
        rows=[]
        mae={}
        for case in selected:
            case_id=case['case_id']
            frame=frames[case_id]
            aggregate=frame.Aggregate.to_numpy().reshape(-1,8).mean(axis=1)
            truth=frame[target].to_numpy().reshape(-1,8).mean(axis=1)[29:-29]
            predicted=predict_appliance_power(model,aggregate,**{k:stats[k] for k in keys},window_size=59)[29:-29]
            if not np.isfinite(predicted).all(): raise ValueError('Nonfinite inference')
            times=(EPOCH+np.arange(len(aggregate))*8)[29:-29]
            rows.append(pd.DataFrame({'case_id':case_id,'Unix':times,'predicted_w':predicted}))
            mae[case_id]=float(np.abs(truth-predicted).mean())
            print(f'{case_id}: {len(predicted)} predictions, MAE {mae[case_id]:.3f} W',flush=True)
        prediction_file=output/'predictions.csv'
        pd.concat(rows,ignore_index=True).to_csv(prediction_file,index=False)
        provenance={'kind':'nilm_checkpoint','checkpoint_sha256':sha256(checkpoint),
            'checkpoint':str(checkpoint.resolve()),'appliance':target,'training_appliance':appliance,
            'sample_seconds':8,'window_size':59,'normalization':stats,
            'prepared_sha256':state.get('prepared_sha256'),'domain_shift':domain_shift,
            'domain_note':'REFIT combined fridge-freezer to synthetic one-node fridge' if domain_shift else 'Synthetic benchmark; not real-house validation',
            'benchmark_sha256':sha256(benchmark/'report.json'),
            'case_sha256':{c['case_id']:c['csv_sha256'] for c in selected},
            'prediction_sha256':sha256(prediction_file),'threads':threads}
        write_json(output/'provenance.json',provenance)
        result=compare_predictions(cases,frames,prediction_file,provenance)
        result['mae_w']=mae
        result['inference_executed']=True
        write_json(output/'comparison.json',result)
        write_json(output/'status.json',{'state':'complete'})
        return result
    except Exception as exc:
        write_json(output/'status.json',{'state':'failed','error':str(exc)})
        raise
    finally:
        torch.set_num_threads(previous_threads)


def generate_benchmark(output: Path, omc: Path | None = None) -> dict[str,Any]:
    if output.exists(): raise FileExistsError(output)
    compiler=find_omc(omc)
    output=output.resolve()
    output.mkdir(parents=True)
    write_json(output/'status.json',{'state':'running'})
    common={'fridge.G':2,'fridge.doorEnabled':False,'Paircon':0,'indoorFanPower':0,
            'Prouter':10,'kettleDurationSeconds':300}
    cases=[]
    frames={}
    try:
        build=output/'build'
        build.mkdir()
        models=[ROOT/'simulation/ElemoniFridge.mo',ROOT/'simulation/ElemoniHouse.mo']
        script=build/'build.mos'
        script.write_text('loadModel(Modelica,{"4.1.0"});\n'+''.join(
            f'loadFile({json.dumps(p.as_posix())});\n' for p in models)+
            'buildModel(ElemoniHouse,stopTime=86400,numberOfIntervals=86400,outputFormat="csv",'
            'variableFilter="(pTotal|pFridge|pKettle)");\ngetErrorString();',encoding='utf-8')
        env=os.environ.copy()
        env['PATH']=str(compiler.parent)+os.pathsep+env.get('PATH','')
        run_command([str(compiler),str(script)],build,output/'build.log',env)
        exe=build/('ElemoniHouse.exe' if os.name=='nt' else 'ElemoniHouse')
        if not exe.exists(): raise RuntimeError('Build failed; see build.log')
        for detector,change in [('fridge',{'fridge.G':5.5}),('kettle',{'kettleDurationSeconds':1200}),
                                ('standby',{'Prouter':65})]:
            for faulty in (False,True):
                case_id=detector+('_fault' if faulty else '_normal')
                overrides={**common,**(change if faulty else {})}
                folder=output/case_id
                folder.mkdir()
                raw=folder/'raw.csv'
                flags=','.join(f'{k}={str(v).lower() if isinstance(v,bool) else v}' for k,v in overrides.items())
                print(case_id,flush=True)
                run_command([str(exe),'-noEventEmit',f'-override={flags}',f'-r={raw}'],build,folder/'simulation.log',env)
                source=pd.read_csv(raw)
                if not np.array_equal(source.time.to_numpy(),np.arange(86401)):
                    raise ValueError('Invalid native simulation grid')
                frame=source.iloc[:-1].rename(columns={'pTotal':'Aggregate','pFridge':'Fridge','pKettle':'Kettle'})
                frame['Unix']=EPOCH+frame.time.to_numpy()
                validate_frame(frame)
                frame.to_csv(folder/'case.csv',index=False)
                frames[case_id]=frame
                cases.append({'case_id':case_id,'detector':detector,'expected_positive':faulty,
                              'overrides':overrides,'csv':f'{case_id}/case.csv',
                              'source_sha256':sha256(raw),'csv_sha256':sha256(folder/'case.csv'),
                              'oracle':detect(detector,frame)})
        for faulty in (False,True):
            case_id='pulse'+('_fault' if faulty else '_normal')
            frame=frames['fridge_normal'].copy()
            if faulty:
                for second in (43210,43230,43250):
                    frame.loc[(frame.time>=second)&(frame.time<second+2),'Aggregate']+=3000
            folder=output/case_id
            folder.mkdir()
            frame.to_csv(folder/'case.csv',index=False)
            frames[case_id]=frame
            cases.append({'case_id':case_id,'detector':'pulse','expected_positive':faulty,
                'csv':f'{case_id}/case.csv','source_sha256':sha256(folder/'case.csv'),
                'csv_sha256':sha256(folder/'case.csv'),'source_case_id':'fridge_normal',
                'intervention':{'kind':'power_pulse_proxy','added_w':3000 if faulty else 0,
                                'starts_seconds':[43210,43230,43250],'duration_seconds':2},
                'oracle':detect('pulse',frame)})
        oracle=confusion([(c['expected_positive'],c['oracle']['positive']) for c in cases])
        report={'synthetic':True,'epoch':EPOCH,'model_sha256':{p.name:sha256(p) for p in models},
                'cases':cases,'oracle_metrics':oracle,'oracle_by_detector':{
                    d:confusion([(c['expected_positive'],c['oracle']['positive']) for c in cases if c['detector']==d])
                    for d in ('fridge','kettle','standby','pulse')},
                'nilm':compare_predictions(cases,frames,None,None),
                'limitations':['Isolated synthetic case-level tests, not household accuracy.',
                               'Increased heat leak is not specific fault diagnosis.',
                               'Power-pulse proxy is not physical electrical arc simulation.']}
        write_json(output/'report.json',report)
        write_json(output/'status.json',{'state':'complete'})
        return report
    except Exception as exc:
        write_json(output/'status.json',{'state':'failed','error':str(exc)})
        raise


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    generation=sub.add_parser('generate')
    generation.add_argument('--output',type=Path,required=True)
    generation.add_argument('--omc',type=Path)
    inference=sub.add_parser('infer')
    inference.add_argument('--benchmark',type=Path,required=True)
    inference.add_argument('--checkpoint',type=Path,required=True)
    inference.add_argument('--output',type=Path,required=True)
    inference.add_argument('--allow-domain-shift',action='store_true')
    inference.add_argument('--threads',type=int,default=4)
    comparison=sub.add_parser('compare')
    comparison.add_argument('--benchmark',type=Path,required=True)
    comparison.add_argument('--predictions',type=Path,required=True)
    comparison.add_argument('--provenance',type=Path,required=True)
    comparison.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='generate':
        report=generate_benchmark(args.output,args.omc)
        print(json.dumps(report['oracle_metrics'],indent=2))
    elif args.command=='infer':
        result=infer_checkpoint(args.benchmark,args.checkpoint,args.output,args.allow_domain_shift,args.threads)
        print(json.dumps(result['metrics'],indent=2))
    else:
        if args.output.exists(): raise FileExistsError(args.output)
        report=json.loads((args.benchmark/'report.json').read_text(encoding='utf-8'))
        frames={c['case_id']:pd.read_csv(args.benchmark/c['csv']) for c in report['cases']}
        result=compare_predictions(report['cases'],frames,args.predictions,
                                   json.loads(args.provenance.read_text(encoding='utf-8')))
        with args.output.open('x',encoding='utf-8') as stream:
            json.dump(result,stream,indent=2,allow_nan=False)
        print(json.dumps(result['metrics'],indent=2))


if __name__=='__main__': main()
