"""Synthetic paired diagnostic benchmark; never claims real household validation."""
from pathlib import Path
import json

import numpy as np
import pandas as pd
import pytest

from src.models.paired_detective import confusion, detect, compare_predictions, generate_benchmark, infer_checkpoint
from tests.test_electrical_model import OMC


def test_metrics_and_unknown() -> None:
    """@spec: SPEC-ELM-BENCH#AC-02
    @spec: SPEC-ELM-BENCH#EC-02
    @tc: BENCH-TC-002
    """
    report = confusion([(True,False),(False,True),(True,True),(False,False),(True,None)])
    assert [report[k] for k in ('tp','fp','tn','fn','not_evaluated')] == [1,1,1,1,1]
    assert report['precision'] == report['recall'] == report['false_positive_rate'] == .5
    assert confusion([])['recall'] is None
    frame = pd.DataFrame({'Unix':np.arange(600)+1767200400,'Aggregate':122.,'Fridge':122.,'Kettle':0.})
    assert detect('fridge',frame)['positive'] is None


def test_prediction_comparison(tmp_path: Path) -> None:
    """@spec: SPEC-ELM-BENCH#AC-03
    @spec: SPEC-ELM-BENCH#EC-01
    @spec: SPEC-ELM-BENCH#EC-02
    @tc: BENCH-TC-003
    """
    epoch=1767200400
    n=86400
    t=np.arange(n)
    kettle=np.where((t>=23400)&(t<24600),1500.,0.)
    case={'case_id':'kettle_fault','detector':'kettle','expected_positive':True}
    frame=pd.DataFrame({'Unix':epoch+t,'Aggregate':kettle+10,'Fridge':2.,'Kettle':kettle})
    times=epoch+np.arange(0,n,8)[29:-29]
    path=tmp_path/'pred.csv'
    # Deliberately wrong synthetic fixture, never saved as real model inference.
    pd.DataFrame({'case_id':'kettle_fault','Unix':times,'predicted_w':0.}).to_csv(path,index=False)
    provenance={'kind':'nilm_checkpoint','checkpoint_sha256':'a'*64,'appliance':'Kettle','sample_seconds':8}
    result=compare_predictions([case],{'kettle_fault':frame},path,provenance)
    assert result['metrics']['fn']==1
    assert result['decision_flips']['lost_positive']==1
    assert result['cases'][0]['aligned_oracle_positive'] is True
    assert compare_predictions([case],{'kettle_fault':frame},None,None)['metrics']['recall'] is None
    bad=pd.read_csv(path).iloc[:-1]
    bad.to_csv(path,index=False)
    with pytest.raises(ValueError): compare_predictions([case],{'kettle_fault':frame},path,provenance)
    with pytest.raises(ValueError): compare_predictions([case],{'kettle_fault':frame},path,{})
    broken=frame.drop(5)
    with pytest.raises(ValueError): detect('kettle',broken)


def test_prediction_false_positive(tmp_path: Path) -> None:
    """@spec: SPEC-ELM-BENCH#AC-03
    @spec: SPEC-ELM-BENCH#EC-01
    @tc: BENCH-TC-003
    """
    times=1767200400+np.arange(86400)
    frame=pd.DataFrame({'Unix':times,'Aggregate':10.,'Fridge':2.,'Kettle':0.})
    case={'case_id':'kettle_normal','detector':'kettle','expected_positive':False}
    path=tmp_path/'pred.csv'
    pd.DataFrame({'case_id':'kettle_normal','Unix':times[::8][29:-29],
                  'predicted_w':1500.}).to_csv(path,index=False)
    meta={'kind':'nilm_checkpoint','checkpoint_sha256':'b'*64,'appliance':'Kettle','sample_seconds':8}
    result=compare_predictions([case],{'kettle_normal':frame},path,meta)
    assert result['metrics']['fp']==1
    assert result['decision_flips']['gained_positive']==1
    assert result['cases'][0]['prediction_above_aggregate_samples']>0
    assert frame.Aggregate.eq(10).all()


def test_checkpoint_inference(tmp_path: Path) -> None:
    """@spec: SPEC-ELM-BENCH#AC-04
    @spec: SPEC-ELM-BENCH#EC-04
    @tc: BENCH-TC-004
    """
    import torch
    from src.models.seq2point import Seq2PointCNN
    from src.models.synthetic_households import sha256
    bench=tmp_path/'bench'
    bench.mkdir()
    n=960
    csv=bench/'case.csv'
    pd.DataFrame({'Unix':1767200400+np.arange(n),'Aggregate':100.,'Fridge':2.,'Kettle':0.}).to_csv(csv,index=False)
    case={'case_id':'fridge_normal','detector':'fridge','expected_positive':False,
          'csv':'case.csv','csv_sha256':sha256(csv)}
    (bench/'report.json').write_text(json.dumps({'cases':[case]}))
    model=Seq2PointCNN(59)
    for param in model.parameters(): param.data.zero_()
    ck={'model_state':model.state_dict(),'window_size':59,'sample_seconds':8,
        'appliance':'synthetic_fridge','normalization':{'agg_mean':100.,'agg_std':10.,'app_mean':2.,'app_std':1.}}
    checkpoint=tmp_path/'fixture.pt'
    torch.save(ck,checkpoint)
    out=tmp_path/'inference'
    result=infer_checkpoint(bench,checkpoint,out,threads=1)
    pred=pd.read_csv(out/'predictions.csv')
    assert len(pred)==120-58
    assert np.allclose(pred.predicted_w,2.)
    assert result['mae_w']['fridge_normal']==pytest.approx(0.)
    assert result['metrics']['not_evaluated']==1  # no complete fridge cycles
    ck['appliance']='fridge_freezer'
    torch.save(ck,checkpoint)
    with pytest.raises(ValueError,match='domain'):
        infer_checkpoint(bench,checkpoint,tmp_path/'crossdomain')
    assert not (tmp_path/'crossdomain').exists()
    ck['appliance']='synthetic_fridge'
    ck['normalization']['agg_std']=0
    torch.save(ck,checkpoint)
    with pytest.raises(ValueError): infer_checkpoint(bench,checkpoint,tmp_path/'invalid')
    ck['normalization']['agg_std']=10
    torch.save(ck,checkpoint)
    csv.write_text(csv.read_text()+'\n')
    with pytest.raises(ValueError,match='hash'):
        infer_checkpoint(bench,checkpoint,tmp_path/'changed-source')


@pytest.mark.skipif(not OMC, reason='omc not installed')
def test_real_pairs(tmp_path: Path) -> None:
    """@spec: SPEC-ELM-BENCH#AC-01
    @spec: SPEC-ELM-BENCH#AC-02
    @spec: SPEC-ELM-BENCH#EC-03
    @tc: BENCH-TC-001
    """
    output=tmp_path/'benchmark'
    report=generate_benchmark(output,Path(str(OMC)))
    assert len(report['cases'])==8
    assert report['oracle_metrics']['tp']==4
    assert report['oracle_metrics']['tn']==4
    assert report['nilm']['status']=='not_evaluated'
    assert report['nilm']['metrics']['recall'] is None
    records={c['case_id']:c for c in report['cases']}
    assert records['fridge_fault']['oracle']['cycle_count']>0
    for key in ('fridge','kettle','standby','pulse'):
        assert records[key+'_normal']['expected_positive'] is False
        assert records[key+'_fault']['expected_positive'] is True
    assert json.loads((output/'status.json').read_text())['state']=='complete'
    with pytest.raises(FileExistsError): generate_benchmark(output,Path(str(OMC)))
