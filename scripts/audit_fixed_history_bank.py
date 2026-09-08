"""Audit all frozen evaluation histories without replacing or sampling any."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from scripts.audit_diagnostic_history_evidence import history_evidence
from src.diagnostic_pilot import read, write_new, file_sha
from src.grounded_partner import grounded_integrity, grounded_candidates
from src.stimulus_audit import SHALLOW, REFERENCES


def rows(path):
    with gzip.open(path, 'rt') as file:
        return [json.loads(line) for line in file]


def audit(source, output):
    manifest = read(source / 'manifest.json')
    for name, sha in manifest['outputs'].items():
        if not (source / name).resolve().is_relative_to(source.resolve()) or file_sha(source / name) != sha:
            raise ValueError('source evidence changed')
    bundles = rows(source / 'evaluation/bundles.jsonl.gz')
    ledger = rows(source / 'evaluation/ledger.jsonl.gz')
    bank = read(source / 'bank_snapshot.json')
    grounded_integrity(read(source / 'design_snapshot.json'), bank, bundles, ledger)
    if len(bundles) != 36:
        raise ValueError('expected all 36 frozen evaluation bundles')
    by_id = {b['bundle_id']: b for b in bundles}
    evidence = {bid: history_evidence(b) for bid, b in by_id.items()}
    categories = Counter(); by_type = defaultdict(Counter)
    for people in evidence.values():
        for person in people:
            highest = person['highest_posterior_types']
            category = ('uniquely_correct' if highest == [person['true_type']] else
                        'tie_includes_true' if person['true_type'] in highest else
                        'wrong_best_type')
            categories[category] += 1; by_type[str(person['true_type'])][category] += 1
    regrets = {}; scored_rows = []
    for policy in (*SHALLOW, *REFERENCES):
        responses = {r['request_id']: r for r in rows(source / f'evaluation/{policy}.responses.jsonl.gz')}
        grouped = defaultdict(lambda: defaultdict(list))
        for row in ledger:
            s = row['spec']
            if s['branch'] not in ('BIND', 'TRANSFER', 'NEAR'):
                continue
            response = responses[row['request_id']]
            if response['prompt_sha256'] != row['prompt_sha256']:
                raise ValueError('response prompt mismatch')
            b = by_id[row['bundle_id']]
            who = 1 - s['recipient'] if s['rebound'] else s['recipient']
            posterior = np.array(evidence[b['bundle_id']][who]['posterior_uniform_prior'])
            _, vectors = grounded_candidates(bank, b, s)
            predicted = .38 + .34 * np.array(vectors).dot(posterior)
            chosen = int(response['raw_response']) - 1
            regret = max(0., float(predicted.max() - predicted[chosen]))
            grouped[s['branch']][b['bundle_id']].append(regret)
            scored_rows.append({'policy': policy, 'request_id': row['request_id'],
                               'expected_values_from_history': predicted.tolist(),
                               'choice': chosen + 1, 'posterior_expected_regret': regret})
        regrets[policy] = {}
        for branch, groups in grouped.items():
            if len(groups) != 36 or any(len(v) != 4 for v in groups.values()):
                raise ValueError('incomplete comparison')
            values = [statistics.mean(v) for v in groups.values()]
            regrets[policy][branch] = {'mean': statistics.mean(values),
                                       'sample_sd': statistics.stdev(values), 'n_bundles': 36,
                                       'bundle_values': dict(zip(groups, values))}
    if any(v['mean'] > 1e-12 for v in regrets['static_belief'].values()):
        raise ValueError('reference posterior and frozen policy disagree')
    result = {'status': 'LOCAL_FIXED_BANK_AUDIT_COMPLETE', 'model_calls': 0, 'new_histories': 0,
              'n_bundles': 36, 'n_participants': 72, 'counts': dict(categories),
              'by_true_type': {k: dict(v) for k, v in by_type.items()},
              'frame_order': ['fairness', 'risk', 'expertise'], 'histories': evidence,
              'regret_definition': 'Best posterior expected candidate value minus selected value. Privileged static Bayesian reference, not actual outcome or a unique internal mechanism.',
              'policy_regret': regrets, 'scored_reference_choices': scored_rows,
              'source_manifest_sha256': file_sha(source / 'manifest.json'),
              'source_script_sha256': file_sha(Path(__file__))}
    output.mkdir(parents=True, exist_ok=False)
    write_new(output / 'summary.json', result)
    lines = ['# Fixed history bank audit', '', 'All 36 frozen evaluation bundles. No new model calls or history draws.',
             '', 'This supplementary audit was specified after the three bundle pilot. It is descriptive, not confirmatory.',
             '', f'Participant evidence categories (n = 72): {dict(categories)}.',
             '', '| Policy | Familiar regret | Composite regret | Paraphrase regret |',
             '| --- | ---: | ---: | ---: |']
    for policy, metrics in regrets.items():
        lines.append('| ' + policy + ' | ' + ' | '.join(f"{metrics[m]['mean']:.5f}" for m in ('BIND', 'TRANSFER', 'NEAR')) + ' |')
    lines += ['', 'Regret uses the static reference assumptions and privileged frame annotations. It is not a measured target success rate.',
              'Zero for the static belief reference is a computational consistency check, not an empirical discovery.',
              'The hidden type oracle knows the actual generator, not just the available history. It can disagree with this evidence based objective.',
              'All participant posteriors, bundle values and reference choices are retained in summary.json. No histories were dropped.', '']
    (output / 'REPORT.md').write_text('\n'.join(lines))
    return {'status': result['status'], 'n_bundles': 36, 'counts': dict(categories), 'model_calls': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.source, args.output)))
