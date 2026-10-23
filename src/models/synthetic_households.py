"""Seeded synthetic Modelica households; see SPEC-ELM-SYNTH. Never trains models."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SPLITS = ('train', 'validation', 'test')
EPOCH = int(datetime.fromisoformat('2026-01-01T00:00:00+07:00').timestamp())
# Deliberately bounded research assumptions, not manufacturer/calibration ranges.
RANGES = {
    'Plights': (18, 90), 'Pfan': (30, 65), 'Ptv': (50, 130), 'Prouter': (6, 18),
    'PriceCook': (450, 800), 'PriceWarm': (20, 60), 'Pkettle': (1200, 2000),
    'Pwash': (250, 600), 'Prinse': (60, 150), 'Pspin': (200, 450),
    'Paircon': (650, 1100), 'loadShiftHours': (-2, 2),
    'roomCapacity': (1.5e6, 3e6), 'roomConductance': (70, 150),
    'roomInitial': (301.15, 305.15), 'outdoorMean': (301.15, 304.15),
    'outdoorAmplitude': (2, 5), 'airconCOP': (2.5, 3.5),
    'fridge.C': (15000, 35000), 'fridge.G': (1.2, 2.8),
    'fridge.Prun': (90, 160), 'fridge.COP': (1.3, 2),
    'fridge.Tamb': (301.15, 306.15), 'fridge.Tinitial': (277.15, 279.15),
    'fridge.Tlow': (275.15, 277.15), 'fridge.Thigh': (278.15, 280.15),
}


def integer(value: Any, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def make_plan(seed: int = 42, train: int = 4, validation: int = 1, test: int = 1,
              duration: int = 86400, cadence: int = 8, window: int = 59) -> dict[str, Any]:
    integer(seed, 'seed', 0)
    rng = random.Random(seed)
    scenarios = []
    for split, count in zip(SPLITS, (train, validation, test)):
        integer(count, split)
        for _ in range(count):
            overrides = {key: round(rng.uniform(low, high), 6) for key, (low, high) in RANGES.items()}
            scenarios.append({'house': f'synthetic-house-{len(scenarios)+1:03d}',
                              'split': split, 'overrides': overrides})
    plan = {'format_version': 1, 'synthetic': True, 'seed': seed,
            'duration_seconds': duration, 'sample_seconds': cadence,
            'window_size': window, 'scenarios': scenarios}
    validate_plan(plan)
    return plan


def validate_plan(plan: dict[str, Any]) -> None:
    if not isinstance(plan, dict) or plan.get('synthetic') is not True or plan.get('format_version') != 1:
        raise ValueError('Expected synthetic format_version=1 plan')
    integer(plan.get('seed'), 'seed', 0)
    duration = integer(plan.get('duration_seconds'), 'duration_seconds')
    cadence = integer(plan.get('sample_seconds'), 'sample_seconds')
    window = integer(plan.get('window_size'), 'window_size')
    if window % 2 != 1 or duration % cadence or duration // cadence < window:
        raise ValueError('Need odd window and complete cadence bins sufficient for a window')
    scenarios = plan.get('scenarios')
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError('scenarios required')
    houses, settings, splits = set(), set(), set()
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise ValueError('Invalid scenario')
        house, split, values = (scenario.get(k) for k in ('house', 'split', 'overrides'))
        if not isinstance(house, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', house) or house in houses:
            raise ValueError('Duplicate or unsafe scenario house ID')
        if split not in SPLITS or not isinstance(values, dict) or set(values) != set(RANGES):
            raise ValueError('Invalid split or override keys')
        for key, (low, high) in RANGES.items():
            value = values[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
                raise ValueError(f'Invalid bounded override: {key}')
        if values['fridge.Tlow'] >= values['fridge.Thigh']:
            raise ValueError('Invalid fridge thermostat')
        signature = json.dumps(values, sort_keys=True)
        if signature in settings:
            raise ValueError('Identical scenarios are not distinct households')
        houses.add(house)
        settings.add(signature)
        splits.add(split)
    if splits != set(SPLITS):
        raise ValueError('Each split requires a distinct scenario')


def convert_csv(source: Path, destination: Path, duration: int, cadence: int,
                epoch: int = EPOCH) -> dict[str, Any]:
    """Strict 1-second Modelica CSV -> aligned mean W and synthetic Unix bins."""
    if destination.exists():
        raise FileExistsError(destination)
    integer(duration, 'duration')
    integer(cadence, 'cadence')
    integer(epoch, 'epoch', 0)
    if duration % cadence:
        raise ValueError('Duration must be divisible by cadence')
    try:
        frame = pd.read_csv(source, usecols=['time', 'pTotal', 'pFridge'])
        values = frame[['time', 'pTotal', 'pFridge']].to_numpy(dtype=np.float64)
    except (ValueError, TypeError) as exc:
        raise ValueError('Expected numeric time,pTotal,pFridge CSV') from exc
    if not len(values) or not np.isfinite(values).all() or (values < 0).any():
        raise ValueError('Empty, nonfinite or negative simulation values')
    times = values[:, 0]
    if (np.diff(times) < 0).any() or not np.allclose(times, np.rint(times), rtol=0, atol=1e-6):
        raise ValueError('Simulation time must be ordered integral seconds')
    if (values[:, 2] > values[:, 1]+1e-6).any():
        raise ValueError('Target exceeds aggregate')
    frame['time'] = np.rint(times).astype(np.int64)
    rows_read = len(frame)
    frame = frame.drop_duplicates('time', keep='last')
    if not np.array_equal(frame['time'].to_numpy(), np.arange(duration+1)):
        raise ValueError('Missing or extra simulation seconds; no gap filling')
    data = frame[['pTotal','pFridge']].to_numpy()[:-1].reshape(-1, cadence, 2).mean(axis=1)
    converted = pd.DataFrame({'Unix': epoch+np.arange(len(data))*cadence,
                              'Aggregate': data[:, 0], 'Fridge': data[:, 1]})
    with destination.open('x', encoding='utf-8', newline='') as stream:
        converted.to_csv(stream, index=False)
    return {'source_sha256': sha256(source), 'output_sha256': sha256(destination),
            'rows_read': rows_read, 'duplicate_rows': rows_read-len(frame),
            'output_rows': len(converted), 'terminal_sample_excluded': True}


def find_omc(explicit: Path | None = None) -> Path:
    candidate = explicit or shutil.which('omc') or next(
        iter(Path('C:/Program Files').glob('OpenModelica*/bin/omc.exe')), None)
    if candidate is None or not Path(candidate).is_file():
        raise FileNotFoundError('OpenModelica omc not found; use --omc PATH')
    return Path(candidate).resolve()


def run_command(args: list[str], cwd: Path, log: Path, env: dict[str, str]) -> None:
    """Execute directly and retain diagnostics, including nonzero exit/timeout."""
    try:
        result = subprocess.run(args, cwd=cwd, env=env, capture_output=True,
                                text=True, errors='replace', timeout=300)
    except subprocess.TimeoutExpired as exc:
        log.write_text(f'Timeout: {exc}', encoding='utf-8')
        raise RuntimeError(f'Command timed out; see {log}') from exc
    log.write_text(result.stdout+'\n'+result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(f'Command failed ({result.returncode}); see {log}')


def frozen_sources(base: Path, plan: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify frozen parent inputs before any destination is created."""
    if json.loads((base/'status.json').read_text(encoding='utf-8')).get('state')!='complete':
        raise ValueError('Base dataset is incomplete')
    original=json.loads((base/'plan.json').read_text(encoding='utf-8'))
    validate_plan(original)
    for key in ('duration_seconds','sample_seconds','window_size'):
        if original[key]!=plan[key]: raise ValueError('Frozen dataset settings changed')
    requested={s['house']:s for s in plan['scenarios']}
    provenance=json.loads((base/'provenance.json').read_text(encoding='utf-8'))
    records={r['house']:r for r in provenance['scenarios']}
    for scenario in original['scenarios']:
        house=scenario['house']
        if requested.get(house)!=scenario or house not in records:
            raise ValueError('Frozen scenario changed or missing')
        record=records[house]
        if any(record.get(k)!=scenario[k] for k in ('split','overrides')):
            raise ValueError('Frozen provenance mismatch')
        for field, digest in (('source','source_sha256'),('csv','output_sha256')):
            path=(base/record[field]).resolve()
            if not path.is_relative_to(base.resolve()) or sha256(path)!=record[digest]:
                raise ValueError('Base source hash mismatch')
    return records, {'path':str(base.resolve()),'plan_sha256':sha256(base/'plan.json'),
        'provenance_sha256':sha256(base/'provenance.json'), 'model_sha256':provenance['model_sha256']}


def extend_dataset(base: Path, output: Path, additional_train: int = 8,
                   seed: int = 43, omc: Path | None = None) -> dict[str, Any]:
    """Add independent train houses without regenerating original validation/test."""
    integer(additional_train,'additional_train')
    original=json.loads((base/'plan.json').read_text(encoding='utf-8'))
    validate_plan(original)
    plan=json.loads(json.dumps(original))
    candidates=make_plan(seed,additional_train,1,1,original['duration_seconds'],
                         original['sample_seconds'],original['window_size'])
    used={s['house'] for s in plan['scenarios']}
    serial=1
    for scenario in candidates['scenarios']:
        if scenario['split']!='train': continue
        while f'synthetic-house-{serial:03d}' in used: serial+=1
        scenario['house']=f'synthetic-house-{serial:03d}'
        used.add(scenario['house'])
        plan['scenarios'].append(scenario)
    plan['seed']=seed
    plan['extension']={'seed':seed,'base_seed':original['seed'],
                       'base_plan_sha256':sha256(base/'plan.json'),'additional_train':additional_train}
    return generate(plan,output,omc,reuse_dataset=base)


def generate(plan: dict[str, Any], output: Path, omc: Path | None = None,
             reuse_dataset: Path | None = None) -> dict[str, Any]:
    """Build once, run all scenarios, strictly convert and prepare; never train."""
    validate_plan(plan)
    if output.exists():
        raise FileExistsError(output)
    reused, parent = frozen_sources(reuse_dataset,plan) if reuse_dataset is not None else ({},None)
    compiler = find_omc(omc)
    models = [ROOT/'simulation/ElemoniFridge.mo', ROOT/'simulation/ElemoniHouse.mo']
    model_hashes = {p.name: sha256(p) for p in models}
    output = output.resolve()
    output.mkdir(parents=True)
    write_json(output/'status.json', {'state':'running'})
    write_json(output/'plan.json', plan)
    duration, cadence = plan['duration_seconds'], plan['sample_seconds']
    env = os.environ.copy()
    env['PATH'] = str(compiler.parent)+os.pathsep+env.get('PATH','')
    try:
        build = output/'build'
        build.mkdir()
        script = build/'build.mos'
        script.write_text('loadModel(Modelica, {"4.1.0"});\n'+
            ''.join(f'loadFile({json.dumps(p.as_posix())});\n' for p in models)+
            f'buildModel(ElemoniHouse, startTime=0, stopTime={duration}, numberOfIntervals={duration}, '
            'outputFormat="csv", variableFilter="(pTotal|pFridge)");\ngetErrorString();\n', encoding='utf-8')
        run_command([str(compiler),str(script)],build,output/'build.log',env)
        executable = build/('ElemoniHouse.exe' if os.name == 'nt' else 'ElemoniHouse')
        if not executable.is_file():
            raise RuntimeError(f'Compiler did not build executable; see {output / "build.log"}')
        manifest: dict[str, Any] = {'appliance':'synthetic_fridge', 'synthetic':True,
            'sample_seconds':cadence, 'window_size':plan['window_size'], **{s:[] for s in SPLITS}}
        records = []
        for i, scenario in enumerate(plan['scenarios'], 1):
            house = scenario['house']
            print(f'[{i}/{len(plan["scenarios"])}] {house} ({scenario["split"]})', flush=True)
            folder = output/house
            folder.mkdir()
            raw = folder/'raw.csv'
            converted = folder/'power.csv'
            if house in reused:
                previous=reused[house]
                shutil.copyfile(reuse_dataset/previous['source'],raw)
                shutil.copyfile(reuse_dataset/previous['csv'],converted)
                if sha256(raw)!=previous['source_sha256'] or sha256(converted)!=previous['output_sha256']:
                    raise ValueError('Copied base hash mismatch')
                record={**previous,'reused_from':str(reuse_dataset.resolve()),
                    'model_sha256':previous.get('model_sha256',parent['model_sha256'])}
            else:
                overrides = ','.join(f'{k}={v:.12g}' for k,v in scenario['overrides'].items())
                run_command([str(executable),'-noEventEmit',f'-override={overrides}',f'-r={raw}'],
                            build,folder/'simulation.log',env)
                record = {**convert_csv(raw,converted,duration,cadence),'model_sha256':model_hashes}
            records.append({**scenario, **record, 'source':raw.relative_to(output).as_posix(),
                            'csv':converted.relative_to(output).as_posix()})
            manifest[scenario['split']].append({'house':house,
                'path':converted.relative_to(output).as_posix(), 'target_column':'Fridge'})
        write_json(output/'provenance.json', {'synthetic':True, 'seed':plan['seed'],
            'model_sha256':model_hashes, 'epoch':EPOCH,
            'epoch_meaning':'Synthetic 2026-01-01 00:00 +07:00, not observations',
            'compiler':str(compiler), 'scenarios':records,'parent_dataset':parent})
        pending = output/'manifest.pending.json'
        write_json(pending,manifest)
        from .nilm_training import prepare
        prepare(pending,output/'prepared.npz')
        windows = {split:len(manifest[split])*(duration//cadence-plan['window_size']+1) for split in SPLITS}
        summary = {'synthetic':True, 'scenarios':len(records), 'sample_seconds':cadence,
                   'duration_seconds':duration, 'windows':windows, 'training_started':False}
        summary.update(reused_scenarios=len(reused),generated_scenarios=len(records)-len(reused))
        write_json(output/'summary.json',summary)
        pending.rename(output/'manifest.json')
        write_json(output/'status.json',{'state':'complete'})
        return summary
    except Exception as exc:
        write_json(output/'status.json',{'state':'failed','error':str(exc)})
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    planning = sub.add_parser('plan')
    planning.add_argument('--output',type=Path,required=True)
    planning.add_argument('--seed',type=int,default=42)
    for split, count in (('train',4),('validation',1),('test',1)):
        planning.add_argument('--'+split,type=int,default=count)
    planning.add_argument('--duration',type=int,default=86400)
    planning.add_argument('--cadence',type=int,default=8)
    planning.add_argument('--window',type=int,default=59)
    generation = sub.add_parser('generate')
    generation.add_argument('--plan',type=Path,required=True)
    generation.add_argument('--output',type=Path,required=True)
    generation.add_argument('--omc',type=Path)
    extension = sub.add_parser('extend')
    extension.add_argument('--base',type=Path,required=True)
    extension.add_argument('--output',type=Path,required=True)
    extension.add_argument('--additional-train',type=int,default=8)
    extension.add_argument('--seed',type=int,default=43)
    extension.add_argument('--omc',type=Path)
    args = parser.parse_args()
    if args.command == 'plan':
        plan = make_plan(args.seed,args.train,args.validation,args.test,args.duration,args.cadence,args.window)
        with args.output.open('x',encoding='utf-8') as stream:
            json.dump(plan,stream,indent=2,allow_nan=False)
        print(f'Plan saved: {args.output}')
    elif args.command == 'extend':
        print(json.dumps(extend_dataset(args.base,args.output,args.additional_train,args.seed,args.omc),indent=2))
    else:
        print(json.dumps(generate(json.loads(args.plan.read_text(encoding='utf-8')),args.output,args.omc),indent=2))


if __name__ == '__main__':
    main()
