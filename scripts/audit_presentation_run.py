"""Postcollection execution audit only. Does not alter the frozen primary scores."""
import argparse
from collections import defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.diagnostic_pilot import digest, file_sha, read, write_new


def audit(run, package):
    contract = read(run / 'analysis_contract.json')
    analyzer = ROOT / 'scripts/analyze_presentation_diagnostic.py'
    plan = ROOT / 'docs/PRESENTATION_DIAGNOSTIC_PLAN_20260909.md'
    if file_sha(analyzer) != contract['analyzer_sha256'] or file_sha(plan) != contract['plan_sha256']:
        raise ValueError('frozen analysis or plan changed')
    packet = read(package / 'package/presentation_packet.json')
    summary = read(run / 'analysis/summary.json')
    if summary['valid'] != 972 or summary['status'] != 'EXPLORATORY_PRESENTATION_DIAGNOSTIC':
        raise ValueError('primary report is not a complete real collection')
    if summary['packet_sha256'] != contract['packet_sha256']:
        raise ValueError('summary packet identity mismatch')
    directory = run / 'retrieved/responses'
    complete = read(directory / 'complete.json')
    paths = sorted(directory.glob('*.response.json'))
    claims = sorted(directory.glob('*.claim.json'))
    records = [read(p) for p in paths]
    if len(records) != 972 or len(claims) != 972:
        raise ValueError('complete audit requires 972 responses and claims')
    if complete['status'] != 'COMPLETE' or complete['responses'] != 972 or complete['mode'] != 'hf':
        raise ValueError('completion identity or count mismatch')
    if complete['direct_correct'] != 36 or summary['direct']['correct'] != 36:
        raise ValueError('direct gate mismatch')
    if complete['packet_sha256'] != contract['packet_sha256']:
        raise ValueError('completion packet identity mismatch')
    if [r['execution_index'] for r in records] != list(range(972)):
        raise ValueError('wrong or repeated execution indices')
    if complete['response_hashes'] != [r['record_sha256'] for r in records]:
        raise ValueError('completion hashes differ from ordered records')
    if len({r['request_id'] for r in records}) != 972:
        raise ValueError('duplicate request identity')
    reported = {r['request_id']: r for r in summary['requests']}
    cpu = {r['request_id']: r for r in read(run / 'tokenizer_check.json')['requests']}
    token_groups = defaultdict(list)
    differing_counts = []
    for path, record, request in zip(paths, records, packet['requests']):
        if record['record_sha256'] != digest({k: v for k, v in record.items() if k != 'record_sha256'}):
            raise ValueError('raw hash mismatch')
        claim = read(path.with_name(path.name.replace('.response.json', '.claim.json')))
        if any(record.get(k) != v for k, v in claim.items()):
            raise ValueError('claim differs from response')
        for field in ('request_id', 'execution_index', 'seed', 'prompt_sha256'):
            if record[field] != request[field]:
                raise ValueError('actual execution differs from packet')
        if record['status'] != 'VALID' or record['failure_type'] is not None:
            raise ValueError('invalid response in complete audit')
        if record['mode'] != 'hf' or record['model'] != summary['model']:
            raise ValueError('wrong provider identity')
        if reported[record['request_id']]['raw_output'] != record['raw_response']:
            raise ValueError('summary changed a response')
        count = record['input_tokens']
        if type(count) is not int or not 0 < count <= 12000:
            raise ValueError('unexpected input token count')
        if count != cpu[record['request_id']]['input_tokens']:
            differing_counts.append(record['request_id'])
        token_groups[f"{request['kind']}/{request.get('layout')}"].append(count)
    inputs = [run / 'analysis/summary.json', run / 'analysis_contract.json',
              run / 'tokenizer_check.json', directory / 'complete.json', analyzer, plan,
              package / 'package/presentation_packet.json', Path(__file__), *paths, *claims]
    return dict(status='COMPLETE_EXECUTION_AUDIT_PASSED', requests=972,
                frozen_analyzer_and_plan_unchanged=True,
                cpu_gpu_input_count_mismatches=differing_counts,
                token_ranges={k: dict(minimum=min(v), maximum=max(v), count=len(v))
                              for k, v in token_groups.items()},
                generation_seconds_sum=sum(r['seconds'] for r in records),
                generation_seconds_excludes='setup, model loading, format checks, retrieval, idle time',
                inputs={str(p): file_sha(p) for p in inputs})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--package', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.run, args.package)
    write_new(args.run / 'postcollection_audit.json', result)
    print({k: v for k, v in result.items() if k != 'inputs'})
