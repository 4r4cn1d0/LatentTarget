from copy import deepcopy
from datetime import datetime,timedelta,timezone
from pathlib import Path
import pytest
from src.diagnostic_pilot import read
from src.diagnostic_extension import validate_extension,collect_extension,check_extension_approval

ROOT=Path(__file__).resolve().parents[1]/'results/diagnostic_extension_package_20260909/package'


@pytest.fixture
def packet():return read(ROOT/'extension_packet.json'),read(ROOT/'packet.json')


def test_frozen_complete_extension(packet,tmp_path):
    p,old=packet
    assert len({r['bundle_id'] for r in p['requests']})==33
    result=collect_extension(p,old,tmp_path/'out')
    assert result['responses']==660
    assert collect_extension(p,old,tmp_path/'out')==result
    assert len(list((tmp_path/'out').glob('*.response.json')))==660


def test_resume_mock_prefix(packet,tmp_path):
    p,old=packet;out=tmp_path/'out'
    assert collect_extension(p,old,out,stop_after=2)['responses']==2
    before=(out/'000.response.json').read_bytes()
    assert collect_extension(p,old,out)['responses']==660
    assert (out/'000.response.json').read_bytes()==before


@pytest.mark.parametrize('change',['seed','prompt','pilot','count','model'])
def test_alterations_fail(packet,change):
    p,old=deepcopy(packet)
    if change=='seed':p['requests'][0]['seed']+=1
    elif change=='prompt':p['requests'][0]['prompt']['user']+=' changed'
    elif change=='pilot':p['requests'][0]['request_id']=old['requests'][0]['request_id']
    elif change=='count':p['new_requests']=661
    else:p['model_config']['generation']['temperature']=0
    with pytest.raises(ValueError):validate_extension(p,old)


def test_failed_response_not_replaced(packet,tmp_path):
    class Failed:
        def set_next_seed(self,seed):pass
        def generate(self,prompt):
            assert not prompt.context
            return 'explanation'
    p,old=packet;out=tmp_path/'out'
    with pytest.raises(RuntimeError):collect_extension(p,old,out,provider_factory=Failed)
    with pytest.raises(RuntimeError):collect_extension(p,old,out)
    assert len(list(out.glob('*.response.json')))==1


def test_approval_fails_closed(packet):
    p,old=packet;sha=validate_extension(p,old)
    with pytest.raises(ValueError):check_extension_approval({},sha)
    a=dict(approved=True,packet_sha256=sha,maximum_requests=660,pod_id='cgy7iwpf6z74qr',
           maximum_total_usd=5,watchdog_verified=True,hourly_quote_usd=1.59,
           pod_deadline_utc=(datetime.now(timezone.utc)+timedelta(minutes=89)).isoformat())
    check_extension_approval(a,sha)
    a['maximum_requests']=720
    with pytest.raises(ValueError):check_extension_approval(a,sha)
