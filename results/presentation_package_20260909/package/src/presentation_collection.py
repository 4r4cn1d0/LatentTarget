"""One fixed guarded run. No automatic retries, replacement choices or hidden state capture."""
from datetime import datetime, timezone
from pathlib import Path
import re
import time

from src.diagnostic_pilot import digest, read, write_new, deadline, real_provider, MockChoiceProvider
from src.focal_agent import FocalPrompt
from src.presentation_diagnostic import validate, N_REQUESTS


def approval_check(approval, sha):
    if (approval.get('approved') is not True or approval.get('packet_sha256') != sha
            or approval.get('maximum_requests') != N_REQUESTS or approval.get('maximum_total_usd') != 5
            or approval.get('watchdog_verified') is not True
            or not re.fullmatch(r'[a-zA-Z0-9_-]+', str(approval.get('pod_id', '')))):
        raise ValueError('scoped approval mismatch')
    if not 0 < approval['hourly_quote_usd'] <= 2:
        raise ValueError('quote outside limit')
    until = datetime.fromisoformat(approval['pod_deadline_utc'])
    if until.tzinfo is None or not 0 < (until - datetime.now(timezone.utc)).total_seconds() <= 5400:
        raise ValueError('deadline expired or too distant')


def collect(packet, pilot, output, mode='mock', approval=None, provider_factory=None):
    sha = validate(packet, pilot)
    if mode not in ('mock', 'hf'):
        raise ValueError('unknown mode')
    if mode == 'hf':
        approval_check(approval or {}, sha)
        if provider_factory is not None:
            raise ValueError('real provider override forbidden')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    identity = dict(packet_sha256=sha, mode=mode, model=pilot['config']['model'] if mode == 'hf' else 'deterministic_mock',
                    approval_sha256=digest(approval) if approval else None)
    write_new(output / 'run.json', identity)
    results = []
    direct_correct = 0
    with deadline(4800):
        provider = real_provider(pilot['config'], output / 'runtime.json') if mode == 'hf' else (provider_factory or MockChoiceProvider)()
        if mode == 'hf':
            from src.hf_provider import _choice_token_sequences
            config = provider._model.generation_config
            fields = ('bos_token_id', 'eos_token_id', 'repetition_penalty', 'suppress_tokens',
                      'begin_suppress_tokens', 'min_length', 'min_new_tokens', 'num_beams')
            write_new(output / 'decoding_audit.json', dict(
                generation_config={k: getattr(config, k, None) for k in fields},
                token_paths=[dict(ids=list(seq), decoded=provider._tok.decode(seq))
                             for seq in _choice_token_sequences(provider._tok, ('1', '2', '3'))]))
        for row in packet['requests']:
            if row['execution_index'] == 36 and mode == 'hf' and direct_correct != 36:
                result = dict(identity, status='DIRECT_CONTROL_FAILED', responses=len(results), planned=N_REQUESTS,
                              direct_correct=direct_correct, response_hashes=[r['record_sha256'] for r in results])
                write_new(output / 'complete.json', result)
                return result
            if mode == 'hf':
                approval_check(approval, sha)
            prompt = FocalPrompt(system=row['prompt']['system'], user=row['prompt']['user'])
            count = None
            if mode == 'hf':
                if provider.capture:
                    raise RuntimeError('activation capture forbidden')
                inputs = provider._format_inputs(prompt.system, prompt.user)
                count = int(inputs['input_ids'].shape[-1])
                del inputs
                if count > 12000:
                    raise RuntimeError('input too long; no truncation')
            claim = dict(identity, request_id=row['request_id'], execution_index=row['execution_index'],
                         prompt_sha256=row['prompt_sha256'], seed=row['seed'])
            write_new(output / f"{row['execution_index']:04d}.claim.json", claim)
            provider.set_next_seed(row['seed'])
            raw, failure = None, None
            started = time.monotonic()
            try:
                raw = provider.generate(prompt)
            except Exception as exc:
                failure = type(exc).__name__
            valid = failure is None and type(raw) is str and raw in ('1', '2', '3')
            result = dict(claim, status='VALID' if valid else 'INVALID_OR_FAILED',
                          raw_response=raw if type(raw) is str else None, failure_type=failure,
                          input_tokens=count, seconds=time.monotonic() - started)
            result['record_sha256'] = digest(result)
            write_new(output / f"{row['execution_index']:04d}.response.json", result)
            results.append(result)
            if not valid:
                raise RuntimeError('failed response retained; no automatic retry')
            if row['kind'] == 'DIRECT':
                direct_correct += raw == row['direct_answer']
            if len(results) % 12 == 0:
                print(dict(completed=len(results), planned=N_REQUESTS, mode=mode), flush=True)
    result = dict(identity, status='COMPLETE', responses=len(results), planned=N_REQUESTS,
                  direct_correct=direct_correct, response_hashes=[r['record_sha256'] for r in results])
    write_new(output / 'complete.json', result)
    return result
