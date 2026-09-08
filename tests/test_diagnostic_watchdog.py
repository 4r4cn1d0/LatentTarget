from datetime import datetime,timedelta,timezone
import json

import pytest

from src.diagnostic_watchdog import safe_pod,watch,RestClient


class Fake:
    def __init__(self,price=1.59):self.status="RUNNING";self.calls=[];self.price=price
    def get(self):
        self.calls.append("GET")
        return {"id":"scoped-pod","desiredStatus":self.status,"costPerHr":self.price,"env":{"SECRET":"not-loggable"}}
    def stop(self):self.calls.append("STOP");self.status="STOPPED"


def run_fake(client,seconds=40):
    current=[datetime(2026,9,8,tzinfo=timezone.utc)];events=[]
    def sleep(s):current[0]+=timedelta(seconds=s)
    watch(client,"scoped-pod",(current[0]+timedelta(seconds=seconds)).isoformat(),events.append,now=lambda:current[0],sleep=sleep)
    return events


def test_deadline_stops_only_once_and_no_secrets_logged():
    c=Fake();events=run_fake(c)
    assert c.calls.count("STOP")==1
    assert events[-1]["event"]=="STOP_CONFIRMED"
    assert "SECRET" not in json.dumps(events) and "not-loggable" not in json.dumps(events)
    assert events[-1]["persistent_storage_still_billed"] is True


def test_expensive_pod_stopped_immediately():
    c=Fake(3);events=run_fake(c)
    assert c.calls==["GET","STOP","GET"]
    assert events[1]["reason"]=="hourly_budget_exceeded"


def test_wrong_id_and_network_volume_fail_before_stop():
    c=Fake();c.get=lambda:{"id":"other","costPerHr":1}
    with pytest.raises(ValueError,match="identity"):run_fake(c)
    assert "STOP" not in c.calls
    c.get=lambda:{"id":"scoped-pod","costPerHr":1,"networkVolumeId":"existing"}
    with pytest.raises(ValueError,match="network-volume"):run_fake(c)
    assert "STOP" not in c.calls


def test_uncertain_stop_response_followed_by_read_confirmation():
    class Uncertain(Fake):
        def stop(self):super().stop();raise TimeoutError()
    c=Uncertain();events=run_fake(c)
    assert events[-1]["event"]=="STOP_CONFIRMED" and c.calls.count("STOP")==1


def test_repeated_read_failure_triggers_scoped_stop():
    class Failing(Fake):
        def get(self):
            if self.calls and self.status=="RUNNING":self.calls.append("GET_FAILED");raise TimeoutError()
            return super().get()
    c=Failing();events=run_fake(c,seconds=300)
    assert c.calls.count("GET_FAILED")==3 and c.calls.count("STOP")==1
    assert any(e.get("reason")=="monitoring_failed" for e in events)


def test_expired_deadline_and_unsafe_ids_refused():
    with pytest.raises(ValueError):run_fake(Fake(),seconds=0)
    with pytest.raises(ValueError):run_fake(Fake(),seconds=8000)
    with pytest.raises(ValueError):RestClient("../other","fixture")


def test_actual_rest_nullable_adjustment_string_price_and_exited():
    p=safe_pod({"id":"scoped-pod","adjustedCostPerHr":None,"costPerHr":"1.59","desiredStatus":"EXITED"},"scoped-pod")
    assert p["hourly_usd"]==1.59 and p["status"]=="EXITED"
    c=Fake();c.status="EXITED"
    events=run_fake(c)
    assert events[-1]["event"]=="STOP_CONFIRMED" and "STOP" not in c.calls
