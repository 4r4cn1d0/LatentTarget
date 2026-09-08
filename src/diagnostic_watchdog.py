"""External deadline watchdog for one explicitly selected diagnostic pod.

Stopping leaves persistent volume charges. This is a safety attempt, not a
provider-enforced billing cap: local machine or network failure can defeat it.
Never logs a full pod response, its environment, or an authentication header.
"""
from datetime import datetime, timezone
import json
import math
import re
import time
import urllib.request


def remaining(deadline, now=None):
    dt=datetime.fromisoformat(deadline)
    if dt.tzinfo is None:raise ValueError("absolute timezone-aware deadline required")
    return (dt-(now or datetime.now(timezone.utc))).total_seconds()


def safe_pod(data, pod_id):
    if data.get("id")!=pod_id:raise ValueError("pod identity mismatch")
    # Only this projection can reach logs.
    price=data.get("adjustedCostPerHr")
    if price is None:price=data.get("costPerHr")
    if isinstance(price,str):
        try:price=float(price)
        except ValueError:raise ValueError("live price unavailable") from None
    if type(price) not in (int,float) or not math.isfinite(price) or price<0:raise ValueError("live price unavailable")
    return {"pod_id":pod_id,"status":data.get("desiredStatus"),"hourly_usd":price,
            "network_volume":bool(data.get("networkVolumeId"))}


class RestClient:
    def __init__(self,pod_id,key):
        if not re.fullmatch(r"[a-zA-Z0-9_-]+",pod_id) or not key:raise ValueError("pod ID and RUNPOD_API_KEY required")
        self.url=f"https://rest.runpod.io/v1/pods/{pod_id}";self.key=key

    def request(self,method,suffix=""):
        req=urllib.request.Request(self.url+suffix,method=method,headers={"Authorization":"Bearer "+self.key,
            "User-Agent":"LatentTarget-Research/1.0","Accept":"application/json"})
        with urllib.request.urlopen(req,timeout=20) as response:
            body=response.read()
            return json.loads(body) if body else {}

    def get(self):return self.request("GET")
    def stop(self):return self.request("POST","/stop")


def watch(client,pod_id,deadline,emit,now=lambda:datetime.now(timezone.utc),sleep=time.sleep):
    seconds=remaining(deadline,now())
    if not 0<seconds<=7200:raise ValueError("deadline must be within two hours")
    initial=safe_pod(client.get(),pod_id)
    if initial["network_volume"]:raise ValueError("network-volume pods cannot use this stop-only watchdog")
    emit({"event":"ARMED",**initial,"deadline_utc":deadline,"billing_cap_guaranteed":False})
    state=initial;failures=0;reason=None
    while True:
        if state and state["status"] in ("STOPPED","EXITED"):
            emit({"event":"STOP_CONFIRMED",**state,"persistent_storage_still_billed":True});return
        if state and state["hourly_usd"]>2:reason="hourly_budget_exceeded";break
        if remaining(deadline,now())<=0:reason="deadline_reached";break
        sleep(min(30,max(.001,remaining(deadline,now()))))
        try:
            state=safe_pod(client.get(),pod_id);failures=0
        except Exception as exc:
            failures+=1;state=None
            emit({"event":"READ_FAILED","failure_type":type(exc).__name__,"consecutive_failures":failures})
            if failures>=3:reason="monitoring_failed";break
    # This stops only the ID explicitly provided, never deletes it or its volume.
    emit({"event":"STOP_REQUESTED","pod_id":pod_id,"reason":reason})
    try:client.stop()
    except Exception as exc:emit({"event":"STOP_RESPONSE_UNCERTAIN","failure_type":type(exc).__name__})
    for _ in range(3):
        try:
            state=safe_pod(client.get(),pod_id)
            if state["status"] in ("STOPPED","EXITED"):
                emit({"event":"STOP_CONFIRMED",**state,"persistent_storage_still_billed":True});return
        except Exception as exc:emit({"event":"STOP_VERIFICATION_FAILED","failure_type":type(exc).__name__})
        sleep(5)
    raise RuntimeError("STOP NOT CONFIRMED: inspect this exact pod immediately; charges may continue")
