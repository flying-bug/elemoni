"""Synthetic-only generation/conversion tests."""
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from src.models.synthetic_households import make_plan, validate_plan, convert_csv, generate, extend_dataset
from src.models.nilm_training import load_prepared
from tests.test_electrical_model import OMC


def test_plan(tmp_path: Path) -> None:
    """@spec: SPEC-ELM-SYNTH#AC-01
    @spec: SPEC-ELM-SYNTH#EC-02
    @tc: SYNTH-TC-001
    """
    a = make_plan(seed=9)
    assert a == make_plan(seed=9)
    assert a != make_plan(seed=10)
    assert len(a['scenarios']) == 6
    assert len({s['house'] for s in a['scenarios']}) == 6
    assert [s['split'] for s in a['scenarios']] == ['train']*4+['validation','test']
    assert len({json.dumps(s['overrides'], sort_keys=True) for s in a['scenarios']}) == 6
    validate_plan(a)
    with pytest.raises(FileExistsError):
        generate(a, tmp_path)


@pytest.mark.parametrize('kind', ['duplicate', 'same', 'empty', 'unknown', 'nan', 'duration', 'bool', 'thermal'])
def test_invalid_plan(kind: str) -> None:
    """@spec: SPEC-ELM-SYNTH#EC-02
    @tc: SYNTH-TC-001
    """
    plan = make_plan()
    scenarios = plan['scenarios']
    if kind == 'duplicate': scenarios[-1]['house'] = scenarios[0]['house']
    if kind == 'same': scenarios[-1]['overrides'] = scenarios[0]['overrides'].copy()
    if kind == 'empty': scenarios[:] = [s for s in scenarios if s['split'] != 'test']
    if kind == 'unknown': scenarios[0]['overrides']['invalid'] = 1
    if kind == 'nan': scenarios[0]['overrides']['Pfan'] = float('nan')
    if kind == 'duration': plan['duration_seconds'] = 17
    if kind == 'bool': plan['sample_seconds'] = True
    if kind == 'thermal': scenarios[0]['overrides']['fridge.Tlow'] = 300
    with pytest.raises(ValueError): validate_plan(plan)


def sample_csv(path: Path) -> None:
    pd.DataFrame({'time':range(17),'pTotal':np.arange(17)+100.,
                  'pFridge':np.arange(17)+10.}).to_csv(path,index=False)


def test_conversion(tmp_path: Path) -> None:
    """@spec: SPEC-ELM-SYNTH#AC-02
    @spec: SPEC-ELM-SYNTH#EC-01
    @tc: SYNTH-TC-002
    """
    source, dest = tmp_path/'raw.csv', tmp_path/'converted.csv'
    sample_csv(source)
    df = pd.read_csv(source)
    event = df.iloc[[4]].copy()
    event['pFridge'] = 99
    pd.concat([df.iloc[:4],event,df.iloc[4:]]).to_csv(source,index=False)
    before = source.read_bytes()
    record = convert_csv(source,dest,duration=16,cadence=8,epoch=1767200400)
    out = pd.read_csv(dest)
    assert out.columns.tolist() == ['Unix','Aggregate','Fridge']
    assert out.Unix.tolist() == [1767200400,1767200408]
    assert out.Aggregate.tolist() == [103.5,111.5]
    assert out.Fridge.tolist() == [13.5,21.5]
    assert out.Aggregate.sum()*8 == pytest.approx(df.pTotal.iloc[:-1].sum())
    assert record['duplicate_rows'] == 1
    assert record['source_sha256'] == hashlib.sha256(before).hexdigest()
    assert source.read_bytes() == before
    with pytest.raises(FileExistsError): convert_csv(source,dest,16,8,1767200400)


@pytest.mark.parametrize('kind', ['nan','negative','gap','reverse','offgrid','target','missing'])
def test_corrupt_csv(tmp_path: Path, kind: str) -> None:
    """@spec: SPEC-ELM-SYNTH#EC-01
    @tc: SYNTH-TC-002
    """
    source = tmp_path/'raw.csv'
    sample_csv(source)
    df = pd.read_csv(source)
    if kind == 'nan': df.loc[3,'pFridge'] = float('nan')
    if kind == 'negative': df.loc[3,'pTotal'] = -1
    if kind == 'gap': df = df.drop(4)
    if kind == 'reverse': df = df.iloc[::-1]
    if kind == 'offgrid':
        df['time'] = df['time'].astype(float)
        df.loc[3,'time'] = 3.5
    if kind == 'target': df.loc[3,'pFridge'] = 999
    if kind == 'missing': df = df.drop(columns=['pTotal'])
    df.to_csv(source,index=False)
    dest = tmp_path/'out.csv'
    with pytest.raises(ValueError): convert_csv(source,dest,16,8,1767200400)
    assert not dest.exists()


@pytest.mark.skipif(not OMC, reason='omc not installed')
def test_generate_real(tmp_path: Path) -> None:
    """@spec: SPEC-ELM-SYNTH#AC-03
    @tc: SYNTH-TC-003
    """
    plan = make_plan(train=1,validation=1,test=1,duration=600,window=3)
    out = tmp_path/'dataset'
    summary = generate(plan,out,omc=Path(str(OMC)))
    assert json.loads((out/'status.json').read_text())['state'] == 'complete'
    data = load_prepared(out/'prepared.npz')
    for split in ('train','validation','test'):
        assert len(data[split]) == 1
        assert len(data[split][0]['time']) == 75
        assert summary['windows'][split] == 73
    assert data['metadata']['manifest']['synthetic'] is True
    provenance = json.loads((out/'provenance.json').read_text())
    assert len(provenance['scenarios']) == 3
    assert len({s['source_sha256'] for s in provenance['scenarios']}) == 3


def test_missing_compiler(tmp_path: Path) -> None:
    """@spec: SPEC-ELM-SYNTH#EC-03
    @tc: SYNTH-TC-004
    """
    with pytest.raises(FileNotFoundError):
        generate(make_plan(),tmp_path/'dataset',omc=tmp_path/'missing.exe')
    assert not (tmp_path/'dataset').exists()


def test_failed_build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """@spec: SPEC-ELM-SYNTH#EC-03
    @tc: SYNTH-TC-004
    """
    def fail(*args: object, **kwargs: object) -> object:
        raise RuntimeError('synthetic compiler failure')
    monkeypatch.setattr('src.models.synthetic_households.run_command',fail)
    out = tmp_path/'dataset'
    with pytest.raises(RuntimeError,match='compiler failure'):
        generate(make_plan(),out,omc=Path(__file__))
    assert json.loads((out/'status.json').read_text())['state'] == 'failed'
    assert not (out/'manifest.json').exists()


@pytest.mark.skipif(not OMC, reason='omc not installed')
def test_extend_real(tmp_path: Path) -> None:
    """@spec: SPEC-ELM-SYNTH#AC-04
    @spec: SPEC-ELM-SYNTH#EC-04
    @tc: SYNTH-TC-005
    """
    base=tmp_path/'base'
    generate(make_plan(train=1,validation=1,test=1,duration=600,window=3),base,Path(str(OMC)))
    before={p.relative_to(base).as_posix():p.read_bytes() for p in base.glob('synthetic-house-*/*.csv')}
    out=tmp_path/'extended'
    summary=extend_dataset(base,out,additional_train=1,seed=43,omc=Path(str(OMC)))
    assert summary['reused_scenarios']==3
    assert summary['generated_scenarios']==1
    assert summary['windows']=={'train':146,'validation':73,'test':73}
    for name,content in before.items():
        assert (out/name).read_bytes()==content
        assert (base/name).read_bytes()==content
    old=json.loads((base/'plan.json').read_text())
    new=json.loads((out/'plan.json').read_text())
    assert new['scenarios'][:3]==old['scenarios']
    assert new['scenarios'][-1]['split']=='train'
    assert new['scenarios'][-1]['house'] not in {s['house'] for s in old['scenarios']}
    changed=base/'synthetic-house-002/power.csv'
    changed.write_bytes(changed.read_bytes()+b'\n')
    with pytest.raises(ValueError,match='hash'):
        extend_dataset(base,tmp_path/'bad',additional_train=1,omc=Path(str(OMC)))
    assert not (tmp_path/'bad').exists()
