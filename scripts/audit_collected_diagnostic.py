"""Descriptive postcollection audit, with an independent vectorized score check."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from src.diagnostic_pilot import read, write_new, file_sha, validate_packet
from src.partner_statistics import bounds_from_choices


def audit(package, run):
    packet = read(package / 'package/packet.json')
    validate_packet(packet)
    key = {r['request_id']: r for r in read(package / 'analyst_key.json')['requests']}
    summary = read(run / 'analysis/summary.json')
    raw_paths = sorted((run / 'retrieved/responses').glob('*.response.json'))
    raw = [read(p) for p in raw_paths]
    assert len(raw) == len({r['request_id'] for r in raw}) == 60
    assert {r['execution_index'] for r in raw} == set(range(60))
    expected = {r['request_id']: r for r in packet['requests']}
    for row in raw:
        assert row['seed'] == expected[row['request_id']]['seed']
        assert row['prompt_sha256'] == expected[row['request_id']]['prompt_sha256']
        assert row['raw_response'] in ('1', '2', '3') and row['failure_type'] is None
    ids = packet['provenance']['selected_bundles']
    choices = np.full((1, 3, 6, 4), -1, dtype=int)
    vectors = np.zeros((3, 6, 3, 3))
    types = np.zeros((3, 2), dtype=int)
    cells = defaultdict(dict)
    for row in raw:
        a = key[row['request_id']]; s = a['spec']; i = ids.index(a['bundle_id'])
        j = {'BIND': 0, 'TRANSFER': 1, 'NEAR': 2, 'RANDOM_RESPONSE': 5}.get(s['branch'])
        if j is None:
            j = 3 if s['bank'] == 'familiar' else 4
        cell = s['recipient'] if s['branch'] == 'NO_HISTORY' else s['cell']
        choices[0, i, j, cell] = int(row['raw_response']) - 1
        vectors[i, j] = a['candidate_vectors']; types[i] = a['types']
        cells[a['bundle_id']].setdefault(s['branch'], {})[str(s['cell'])] = {
            'digit': row['raw_response'],
            'vector': a['candidate_vectors'][int(row['raw_response']) - 1],
        }
    lo, hi = bounds_from_choices(types, vectors, choices)
    np.testing.assert_allclose(lo.mean(1)[0], summary['mean_lower'], atol=1e-12)
    np.testing.assert_allclose(hi.mean(1)[0], summary['mean_upper'], atol=1e-12)
    metrics = {}
    for m in summary['metric_order']:
        values = [summary['bundle_bounds'][bid][m][0] for bid in ids]
        metrics[m] = {'n_bundles': 3, 'values': values, 'mean': statistics.mean(values),
                      'sample_sd': statistics.stdev(values), 'min': min(values), 'max': max(values)}
    duration = [r['seconds'] for r in raw]
    return {
        'status': 'AUDIT_PASSED', 'independent_score_check': True,
        'description': 'Postcollection descriptive inspection. No model calls or hypothesis tests.',
        'raw_choice_counts': dict(Counter(r['raw_response'] for r in raw)),
        'input_tokens_min': min(r['input_tokens'] for r in raw),
        'input_tokens_max': max(r['input_tokens'] for r in raw),
        'generation_seconds_sum': sum(duration), 'generation_seconds_median': statistics.median(duration),
        'generation_seconds_min': min(duration), 'generation_seconds_max': max(duration),
        'metrics': metrics, 'all_cells': dict(cells),
        'inputs': {str(p): file_sha(p) for p in [*raw_paths, run / 'analysis/summary.json',
                   package / 'analyst_key.json', package / 'package/packet.json', Path(__file__),
                   ROOT / 'src/partner_statistics.py']},
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.package, args.run)
    write_new(args.run / 'postcollection_audit.json', result)
    print(json.dumps({k: v for k, v in result.items() if k not in ('all_cells', 'inputs')}))
