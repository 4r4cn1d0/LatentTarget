"""Complete the fixed 36 bundle bank without rerunning the three pilot bundles."""
from collections import Counter
from datetime import datetime, timezone
import fcntl
from pathlib import Path
import re
import time

from src.diagnostic_pilot import (digest, read, write_new, validate_packet, real_provider,
                                  deadline, MockChoiceProvider)
from src.focal_agent import FocalPrompt


def validate_extension(packet, pilot):
    prior_sha = validate_packet(pilot)
    if packet['pilot_packet_sha256'] != prior_sha or packet['model_config'] != pilot['config']:
        raise ValueError('pilot identity or model settings differ')
    if packet['new_requests'] != 660 or packet['combined_requests'] != 720 or len(packet['requests']) != 660:
        raise ValueError('extension must complete exactly 33 bundles')
    prior_ids = {r['request_id'] for r in pilot['requests']}
    groups = Counter(); ids = set()
    for i, row in enumerate(packet['requests']):
        rid = row['request_id']; spec = row['spec']; cell = spec['cell']
        if rid in ids or rid in prior_ids or rid != f"{row['bundle_id']}/{spec['branch']}/{cell}":
            raise ValueError('duplicate or previously completed request')
        if row['bundle_id'] in pilot['provenance']['selected_bundles']:
            raise ValueError('pilot bundle cannot be rerun')
        if spec['branch'] not in ('BIND', 'NEAR', 'TRANSFER', 'NO_HISTORY', 'RANDOM_RESPONSE') or cell not in range(4):
            raise ValueError('unexpected branch')
        bank = ('familiar' if cell < 2 else 'composite') if spec['branch'] == 'NO_HISTORY' else {'BIND':'familiar','NEAR':'near','TRANSFER':'composite','RANDOM_RESPONSE':'familiar'}[spec['branch']]
        if spec != dict(branch=spec['branch'], cell=cell, bank=bank, recipient=cell % 2,
                        rebound=False if spec['branch']=='NO_HISTORY' else cell >= 2):
            raise ValueError('cell specification changed')
        if row['execution_index'] != i or row['seed'] != int(digest([202609089, rid])[:8], 16):
            raise ValueError('execution schedule changed')
        if set(row['prompt']) != {'system','user'} or digest(row['prompt']) != row['prompt_sha256']:
            raise ValueError('prompt changed or contains analyst metadata')
        ids.add(rid); groups[(row['bundle_id'],spec['branch'])] += 1
    if len(groups) != 165 or set(groups.values()) != {4}:
        raise ValueError('incomplete branch allocation')
    return digest(packet)


def check_extension_approval(approval, sha):
    if (approval.get('approved') is not True or approval.get('packet_sha256') != sha
        or approval.get('maximum_requests') != 660 or not re.fullmatch(r'[a-zA-Z0-9_-]+', str(approval.get('pod_id','')))
        or approval.get('maximum_total_usd') != 5 or approval.get('watchdog_verified') is not True):
        raise ValueError('extension approval mismatch')
    dt = datetime.fromisoformat(approval['pod_deadline_utc'])
    if dt.tzinfo is None or not 0 < (dt - datetime.now(timezone.utc)).total_seconds() <= 5400:
        raise ValueError('extension deadline missing or expired')
    if not 0 < approval['hourly_quote_usd'] <= 2:
        raise ValueError('hourly quote exceeds limit')


def collect_extension(packet, pilot, output, mode='mock', approval=None, provider_factory=None, stop_after=None):
    sha = validate_extension(packet, pilot)
    if mode not in ('mock','hf'):
        raise ValueError('unknown mode')
    if mode == 'hf':
        check_extension_approval(approval or {}, sha)
        if provider_factory or stop_after is not None:
            raise ValueError('real provider overrides forbidden')
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    identity = {'packet_sha256':sha, 'pilot_packet_sha256':packet['pilot_packet_sha256'],
                'mode':mode, 'model':pilot['config']['model'] if mode=='hf' else 'deterministic_mock',
                'approval_sha256':digest(approval) if approval else None}
    with (output/'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (output/'run.json').exists():
            if read(output/'run.json') != identity:
                raise ValueError('output belongs to another run')
        else:
            if {p.name for p in output.iterdir()} != {'run.lock'}:
                raise ValueError('nonempty output without identity')
            write_new(output/'run.json',identity)
        completed=[]; pending=[]
        allowed={'run.lock','run.json','complete.json','runtime.json'}
        for row in packet['requests']:
            index=row['execution_index']; cp=output/f'{index:03d}.claim.json'; rp=output/f'{index:03d}.response.json'
            allowed.update((cp.name,rp.name))
            claim=dict(identity,request_id=row['request_id'],prompt_sha256=row['prompt_sha256'],seed=row['seed'])
            if rp.exists() and not cp.exists():
                raise ValueError('unclaimed response')
            if cp.exists():
                if read(cp)!=claim or not rp.exists():
                    raise RuntimeError('uncertain or changed prior call; no retry')
                response=read(rp)
                if response.get('record_sha256')!=digest({k:v for k,v in response.items() if k!='record_sha256'}) or any(response.get(k)!=v for k,v in claim.items()):
                    raise ValueError('response identity or hash changed')
                if response.get('status')!='VALID' or response.get('raw_response') not in ('1','2','3'):
                    raise RuntimeError('failed response retained; no replacement')
                completed.append(response)
            else:
                pending.append((row,claim,cp,rp))
        if set(p.name for p in output.iterdir()) - allowed:
            raise ValueError('unexpected collection files')
        if completed and pending and max(r['execution_index'] for r in completed) >= pending[0][0]['execution_index']:
            raise ValueError('completed records not a prefix')
        completion=dict(identity,status='COMPLETE',responses=660,scientific_result=False,
                        response_hashes=[r['record_sha256'] for r in completed])
        if not pending:
            if read(output/'complete.json') != completion:
                raise ValueError('completion manifest differs')
            return completion
        if (output/'complete.json').exists():
            raise ValueError('premature completion marker')
        with deadline(4800):
            if mode=='hf' and (output/'runtime.json').exists():
                raise RuntimeError('prior real runtime exists; inspect before resuming')
            provider=real_provider(pilot['config'],output/'runtime.json') if mode=='hf' else (provider_factory or MockChoiceProvider)()
            for called,(row,claim,cp,rp) in enumerate(pending,1):
                if mode=='hf':
                    check_extension_approval(approval,sha)
                prompt=FocalPrompt(system=row['prompt']['system'],user=row['prompt']['user'])
                count=None
                if mode=='hf':
                    if provider.capture:raise RuntimeError('activation capture forbidden')
                    inputs=provider._format_inputs(prompt.system,prompt.user);count=int(inputs['input_ids'].shape[-1]);del inputs
                    if count>12000:raise RuntimeError('input too long; no truncation')
                provider.set_next_seed(row['seed']);write_new(cp,claim);started=time.monotonic()
                raw=None;failure=None
                try:raw=provider.generate(prompt)
                except Exception as exc:failure=type(exc).__name__
                valid=failure is None and type(raw) is str and raw in ('1','2','3')
                record=dict(claim,execution_index=row['execution_index'],status='VALID' if valid else 'INVALID_OR_FAILED',
                            raw_response=raw if type(raw) is str else None,failure_type=failure,input_tokens=count,
                            seconds=time.monotonic()-started)
                record['record_sha256']=digest(record);write_new(rp,record)
                if not valid:raise RuntimeError('failed response recorded; no fallback or retry')
                completed.append(record)
                print({'completed':len(completed),'planned':660,'mode':mode},flush=True)
                if stop_after is not None and called>=stop_after:
                    return dict(identity,status='MOCK_PAUSED',responses=len(completed))
        completion['response_hashes']=[r['record_sha256'] for r in completed]
        write_new(output/'complete.json',completion)
        return completion
