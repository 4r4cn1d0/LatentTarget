"""Audit how informative the existing pilot histories were, without new draws."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from src.diagnostic_pilot import read, write_new, file_sha
from src.partner_policies import state_values


def history_evidence(bundle):
    counts = np.zeros((2, 3, 2), dtype=int)
    for event in bundle['events']:
        counts[bundle['aliases'].index(event['participant']), event['analyst_frame'], int(event['choice'] == 'A')] += 1
    result = []
    for who, alias in enumerate(bundle['aliases']):
        log_likelihood = []
        for target in range(3):
            p = .38 + .34 * (np.arange(3) == target)
            log_likelihood.append(np.sum(counts[who, :, 1] * np.log(p) + counts[who, :, 0] * np.log1p(-p)))
        likelihood = np.exp(np.array(log_likelihood) - max(log_likelihood))
        posterior = likelihood / likelihood.sum()
        result.append({'alias': alias, 'true_type': bundle['types'][who],
                       'a_counts': counts[who, :, 1].tolist(), 'b_counts': counts[who, :, 0].tolist(),
                       'posterior_uniform_prior': posterior.tolist(),
                       'highest_posterior_types': np.flatnonzero(posterior >= max(posterior) - 1e-12).tolist()})
    events = bundle['events']
    q = state_values(np.array([[e['analyst_frame'] for e in events]]),
                     np.array([[bundle['aliases'].index(e['participant']) for e in events]]),
                     np.array([[e['choice'] == 'A' for e in events]]), 'static_belief', {'initial_reward': .5})
    np.testing.assert_allclose((q[0] - .38) / .34, [r['posterior_uniform_prior'] for r in result], atol=1e-12)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analyst-key', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = {'description': 'Postcollection descriptive evidence audit; no new model calls, history replacement or inference tests.',
              'frame_order': ['fairness', 'risk', 'expertise'],
              'assumptions': 'Uniform prior; independent static types; exact privileged frame annotations and simulator likelihoods.',
              'source_sha256': file_sha(args.analyst_key), 'script_sha256': file_sha(Path(__file__)),
              'bundles': {b['bundle_id']: history_evidence(b) for b in read(args.analyst_key)['bundles']}}
    write_new(args.output, result)
    print(json.dumps(result))
