"""Postcollection descriptives and execution checks. No model calls or tests of hypotheses."""
import argparse
from collections import Counter
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.diagnostic_pilot import digest, file_sha, read, write_new


def describe(values):
    if len(values) < 2:
        raise ValueError('at least two bundles required')
    return dict(n_bundles=len(values), mean=statistics.mean(values),
                sample_sd=statistics.stdev(values), median=statistics.median(values),
                minimum=min(values), maximum=max(values),
                positive=sum(v > 0 for v in values), zero=sum(v == 0 for v in values),
                negative=sum(v < 0 for v in values))


def audit(run, prior):
    summary_path = run / 'analysis/summary.json'
    summary = read(summary_path)
    if not summary['complete'] or summary['valid_choices'] != 720:
        raise ValueError('this complete collection audit requires all 720 choices')
    contract_path = run / 'analysis_contract.json'
    contract = read(contract_path)
    analyzer = ROOT / 'scripts/analyze_diagnostic_extension.py'
    if file_sha(analyzer) != contract['analyzer_sha256']:
        raise ValueError('frozen analyzer changed')
    raw = []
    inputs = [summary_path, contract_path, analyzer, Path(__file__)]
    for directory, count in ((prior, 60), (run / 'retrieved/responses', 660)):
        paths = sorted(directory.glob('*.response.json'))
        records = [read(p) for p in paths]
        if len(records) != count or {r['execution_index'] for r in records} != set(range(count)):
            raise ValueError('incomplete or duplicate execution indices')
        for path, record in zip(paths, records):
            claim_path = path.with_name(path.name.replace('.response.json', '.claim.json'))
            claim = read(claim_path)
            if any(record.get(k) != v for k, v in claim.items()):
                raise ValueError('claim mismatch')
            if record['record_sha256'] != digest({k: v for k, v in record.items() if k != 'record_sha256'}):
                raise ValueError('record hash changed')
            if record['failure_type'] is not None or record['status'] != 'VALID' or record['raw_response'] not in ('1', '2', '3'):
                raise ValueError('failed output in complete report')
            inputs.append(claim_path)
        completion_path = directory / 'complete.json'
        completion = read(completion_path)
        if completion['status'] != 'COMPLETE' or completion['responses'] != count:
            raise ValueError('completion marker mismatch')
        # The extension additionally records the ordered response hash vector.
        if count == 660 and completion['response_hashes'] != [r['record_sha256'] for r in records]:
            raise ValueError('completion hash vector mismatch')
        raw.extend(records)
        inputs.extend([*paths, completion_path])
    if len({r['request_id'] for r in raw}) != 720:
        raise ValueError('repeated request across collections')
    by_id = {r['request_id']: r for r in raw}
    if {r['request_id'] for r in summary['requests']} != set(by_id):
        raise ValueError('summary membership mismatch')
    for request in summary['requests']:
        if request['raw_output'] != by_id[request['request_id']]['raw_response']:
            raise ValueError('summary choice changed')
    metrics = {name: describe(list(values)) for name, values in
               zip(summary['metric_order'], zip(*summary['bundle_lower']))}
    return dict(status='COMPLETE_COLLECTION_AUDIT_PASSED', description=__doc__,
                frozen_analyzer_unchanged=True, requests=720, new_requests=660,
                original_requests=60, metrics=metrics,
                digit_counts=dict(Counter(r['raw_response'] for r in raw)),
                input_tokens_min=min(r['input_tokens'] for r in raw),
                input_tokens_max=max(r['input_tokens'] for r in raw),
                generation_seconds_sum=sum(r['seconds'] for r in raw),
                generation_seconds_excludes='setup, model loading, preflight, retrieval and idle time',
                inputs={str(p): file_sha(p) for p in inputs})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--prior', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.run, args.prior)
    write_new(args.run / 'postcollection_audit.json', result)
    print({k: v for k, v in result.items() if k != 'inputs'})
