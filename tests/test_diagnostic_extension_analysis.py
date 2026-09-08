"""Synthetic extension records below are test fixtures, not experimental data."""
import json
from pathlib import Path
import pytest
from src.diagnostic_pilot import read,digest
from scripts.analyze_diagnostic_extension import analyze
from scripts.verify_extension_scores import verify

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'results/grounded_partner_readiness_20260908'
PACKAGE=ROOT/'results/diagnostic_extension_package_20260909/package'
PRIOR=ROOT/'results/runpod_diagnostic_20260909/retrieved/responses'


def fixture_run(tmp_path,invalid=False):
    packet=read(PACKAGE/'extension_packet.json');out=tmp_path/'synthetic_fixture';out.mkdir()
    identity={'mode':'hf','model':packet['model_config']['model'],'packet_sha256':digest(packet),
              'pilot_packet_sha256':packet['pilot_packet_sha256'],'approval_sha256':'synthetic-test-fixture'}
    (out/'run.json').write_text(json.dumps(identity))
    # Exactly one fixture response, leaving 659 genuinely missing test cells.
    spec=packet['requests'][0]
    row=dict(identity,request_id=spec['request_id'],prompt_sha256=spec['prompt_sha256'],seed=spec['seed'],
             status='INVALID_OR_FAILED' if invalid else 'VALID',raw_response='1 ' if invalid else '1')
    row['record_sha256']=digest(row)
    (out/'000.response.json').write_text(json.dumps(row))
    return out


@pytest.mark.parametrize('invalid',[False,True])
def test_missing_retained_and_strict_status_respected(tmp_path,invalid):
    new=fixture_run(tmp_path,invalid)
    result=analyze(SOURCE,PACKAGE,PRIOR,new,tmp_path/'report')
    assert result['valid_choices']==(60 if invalid else 61)
    assert not result['complete']
    summary=read(tmp_path/'report/summary.json')
    assert len(summary['requests'])==720 and summary['unrequested_forecasts']==144
    assert sum(r['status']=='missing' for r in summary['requests'])==659
    assert summary['posterior_regret']=={}
    assert any(lo<hi for lo,hi in zip(summary['mean_lower'],summary['mean_upper']))
    assert summary['confidence_intervals'] is None
    assert verify(SOURCE,tmp_path/'report/summary.json')['status']=='INDEPENDENT_SCORE_CHECK_PASSED'


def test_duplicate_prior_in_extension_fails(tmp_path):
    new=fixture_run(tmp_path)
    old=read(PRIOR/'000.response.json')
    (new/'001.response.json').write_text(json.dumps(old))
    with pytest.raises(ValueError):analyze(SOURCE,PACKAGE,PRIOR,new,tmp_path/'report')
