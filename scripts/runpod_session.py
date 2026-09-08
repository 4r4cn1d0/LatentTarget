"""Ephemeral authenticated RunPod control session; credentials stay in memory.

First stdin line is the API key. Subsequent lines are JSON commands. Only
read-only queries and one scoped diagnostic pod creation/stop are supported.
Nothing reads or modifies another project's pod. No secret enters logs.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import sys
import termios
import threading
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.diagnostic_pilot import write_new,read,digest
from src.diagnostic_watchdog import watch


def projection(p):
    return {k:p.get(k) for k in ('id','name','desiredStatus','costPerHr','adjustedCostPerHr','gpu','publicIp','portMappings','lastStartedAt','volumeInGb','volumeMountPath','containerDiskInGb','networkVolumeId','networkVolume','image','imageName')}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out-dir',type=Path,required=True);a=parser.parse_args()
    a.out_dir.mkdir(parents=True,exist_ok=True)
    # A PTY permits interactive control, but its input must not echo credentials.
    if sys.stdin.isatty():
        state=termios.tcgetattr(sys.stdin.fileno());state[3]&=~termios.ECHO;termios.tcsetattr(sys.stdin.fileno(),termios.TCSANOW,state)
    print('AWAITING_KEY_STDIN_NO_ECHO',flush=True)
    key=sys.stdin.readline().strip().replace('\\_','_')
    if not re.fullmatch(r'rpa_[A-Za-z0-9]+',key):raise ValueError('invalid credential format; value not displayed')
    scoped_id=None;thread=None;armed=threading.Event();events=[];guard=threading.Lock()

    def emit(value):
        with guard:
            line=json.dumps(value,allow_nan=False)
            with (a.out_dir/'control_events.jsonl').open('a') as f:f.write(line+'\n');f.flush();os.fsync(f.fileno())
            print(line,flush=True)

    def request(method,path,body=None,graphql=False):
        base='https://api.runpod.io/graphql' if graphql else 'https://rest.runpod.io/v1'
        req=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,
             headers={'Authorization':'Bearer '+key,'Content-Type':'application/json',
                      'User-Agent':'LatentTarget-Research/1.0','Accept':'application/json'},method=method)
        try:
            with urllib.request.urlopen(req,timeout=30) as r:
                data=r.read();return json.loads(data) if data else {}
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f'RunPod HTTP {exc.code}; response body withheld') from None

    class ScopedClient:
        def get(self):return request('GET','/pods/'+scoped_id)
        def stop(self):return request('POST','/pods/'+scoped_id+'/stop')

    def watchdog_event(e):
        events.append(e);emit(e)
        if e['event']=='ARMED':armed.set()

    def guard_pod(deadline):
        try:watch(ScopedClient(),scoped_id,deadline,watchdog_event)
        except Exception as exc:
            emit({'event':'WATCHDOG_FAILED','failure_type':type(exc).__name__})
            # Best-effort scoped stop if the guard fails after allocation.
            try:request('POST','/pods/'+scoped_id+'/stop');emit({'event':'EMERGENCY_STOP_SENT','pod_id':scoped_id})
            except Exception as stop_exc:emit({'event':'EMERGENCY_STOP_UNCONFIRMED','failure_type':type(stop_exc).__name__})

    emit({'event':'KEY_ACCEPTED_IN_MEMORY'})
    for line in sys.stdin:
        try:
            command=json.loads(line);op=command['op']
            if op=='list':emit({'event':'PODS','pods':[projection(p) for p in request('GET','/pods')]})
            elif op=='get':
                pid=command['pod_id']
                if not re.fullmatch(r'[a-zA-Z0-9_-]+',pid):raise ValueError('invalid pod ID')
                emit({'event':'POD','pod':projection(request('GET','/pods/'+pid))})
            elif op=='graphql':
                q=command['query']
                if not q.lstrip().startswith('query') or re.search(r'\bmutation\b',q):raise ValueError('read-only query required')
                data=request('POST','',{'query':q},graphql=True)
                emit({'event':'READ_QUERY','result':data})
            elif op=='create':
                if scoped_id is not None or (a.out_dir/'create_claim.json').exists():raise ValueError('creation already attempted; do not repeat')
                payload=read(command['payload_file'])
                expected_name=('latenttarget-presentation-20260909' if command.get('presentation') is True else
                               'latenttarget-diagnostic-extension-20260909' if command.get('extension') is True else 'latenttarget-diagnostic-20260909')
                if (payload.get('name')!=expected_name or payload.get('gpuCount')!=1
                    or payload.get('networkVolumeId') or payload.get('volumeInGb')!=150 or payload.get('containerDiskInGb')!=20
                    or payload.get('cloudType')!='SECURE' or payload.get('interruptible') is not False):raise ValueError('deployment scope mismatch')
                quote=command['hourly_quote_usd']
                if type(quote) not in (int,float) or not 0<quote<=2:raise ValueError('live quote exceeds approved limit')
                started=datetime.now(timezone.utc);deadline=(started+timedelta(minutes=90 if command.get('extension') is True or command.get('presentation') is True else 120)).isoformat()
                write_new(a.out_dir/'create_claim.json',{'payload_sha256':digest(payload),'hourly_quote_usd':quote,'started_utc':started.isoformat(),'deadline_utc':deadline})
                p=request('POST','/pods',payload);scoped_id=p['id']
                write_new(a.out_dir/'created_pod.json',{'pod':projection(p),'deadline_utc':deadline})
                thread=threading.Thread(target=guard_pod,args=(deadline,),daemon=False);thread.start()
                emit({'event':'CREATED','pod':projection(p),'deadline_utc':deadline})
            elif op=='resume_presentation':
                if scoped_id is not None or (a.out_dir/'resume_claim.json').exists():raise ValueError('resume already attempted')
                pid='i0szqs87ifg0id'
                backup=read(ROOT/'results/runpod_extension_20260909/backup_receipt.json')
                if backup.get('status')!='BACKUP_VERIFIED' or backup.get('pod_id')!=pid:raise ValueError('extension backup must be verified')
                package=ROOT/'results/presentation_package_20260909/package'
                from src.diagnostic_pilot import verify_package
                from src.presentation_diagnostic import validate
                verify_package(package)
                packet_sha=validate(read(package/'presentation_packet.json'),read(package/'packet.json'))
                p=request('GET','/pods/'+pid)
                from src.diagnostic_watchdog import safe_pod
                safe=safe_pod(p,pid)
                if (p.get('name')!='latenttarget-diagnostic-extension-20260909' or safe['network_volume']
                    or safe['status'] not in ('EXITED','STOPPED') or not 0<safe['hourly_usd']<=2
                    or p.get('volumeInGb')!=150):raise ValueError('existing extension pod scope or quote changed')
                started=datetime.now(timezone.utc);deadline=(started+timedelta(minutes=90)).isoformat()
                claim={'pod_id':pid,'packet_sha256':packet_sha,'maximum_requests':972,'maximum_total_usd_including_prior_runs':5,
                       'started_utc':started.isoformat(),'deadline_utc':deadline,'hourly_quote_usd':safe['hourly_usd']}
                write_new(a.out_dir/'resume_claim.json',claim);scoped_id=pid
                try:request('POST','/pods/'+pid+'/start')
                finally:
                    thread=threading.Thread(target=guard_pod,args=(deadline,),daemon=False);thread.start()
                emit({'event':'RESUMED_PRESENTATION',**claim})
            elif op=='resume_extension':
                if scoped_id is not None or (a.out_dir/'resume_claim.json').exists():raise ValueError('resume already attempted')
                pid='cgy7iwpf6z74qr'
                backup=read(ROOT/'results/runpod_diagnostic_20260909/backup_receipt.json')
                if backup.get('status')!='BACKUP_VERIFIED' or backup.get('pod_id')!=pid:raise ValueError('pilot backup must be verified')
                packet=read(ROOT/'results/diagnostic_extension_package_20260909/package/extension_packet.json')
                from src.diagnostic_extension import validate_extension
                packet_sha=validate_extension(packet,read(ROOT/'results/diagnostic_extension_package_20260909/package/packet.json'))
                p=request('GET','/pods/'+pid)
                from src.diagnostic_watchdog import safe_pod
                safe=safe_pod(p,pid)
                if (p.get('name')!='latenttarget-diagnostic-20260909' or safe['network_volume']
                    or safe['status'] not in ('EXITED','STOPPED') or not 0<safe['hourly_usd']<=2
                    or p.get('volumeInGb')!=150):raise ValueError('existing diagnostic pod scope or quote changed')
                started=datetime.now(timezone.utc);deadline=(started+timedelta(minutes=90)).isoformat()
                claim={'pod_id':pid,'packet_sha256':packet_sha,'maximum_requests':660,'maximum_total_usd_including_pilot':5,
                       'started_utc':started.isoformat(),'deadline_utc':deadline,'hourly_quote_usd':safe['hourly_usd']}
                write_new(a.out_dir/'resume_claim.json',claim);scoped_id=pid
                try:request('POST','/pods/'+pid+'/start')
                finally:
                    thread=threading.Thread(target=guard_pod,args=(deadline,),daemon=False);thread.start()
                emit({'event':'RESUMED_EXTENSION',**claim})
            elif op=='status':
                if not scoped_id:raise ValueError('no scoped pod created')
                emit({'event':'STATUS','pod':projection(request('GET','/pods/'+scoped_id)),'watchdog_armed':armed.is_set(),'watchdog_alive':thread.is_alive()})
            elif op=='stop':
                if not scoped_id:raise ValueError('no scoped pod created')
                request('POST','/pods/'+scoped_id+'/stop');emit({'event':'STOP_SENT','pod_id':scoped_id})
            elif op=='exit':
                if thread and thread.is_alive():raise ValueError('watchdog still active; confirm stopped status before exiting')
                emit({'event':'CLOSED'});break
            else:raise ValueError('unsupported operation')
        except Exception as exc:
            emit({'event':'COMMAND_FAILED','failure_type':type(exc).__name__,'safe_message':str(exc) if isinstance(exc,(ValueError,RuntimeError)) else 'details withheld'})


if __name__=='__main__':main()
