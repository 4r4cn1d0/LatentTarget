"""Fixed descriptive analysis of presentation and order. No significance search."""
import argparse
from collections import Counter, defaultdict
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from src.diagnostic_pilot import read, write_new, file_sha, digest, verify_package
from src.presentation_diagnostic import validate, FORMATS
from src.partner_statistics import bounds_from_choices


def stats(values):
    return dict(n_bundles=len(values), mean=statistics.mean(values), sample_sd=statistics.stdev(values),
                median=statistics.median(values), minimum=min(values), maximum=max(values))


def analyze(package_root, responses, output, allow_mock=False):
    verify_package(package_root / 'package')
    packet = read(package_root / 'package/presentation_packet.json')
    pilot = read(package_root / 'package/packet.json')
    sha = validate(packet, pilot)
    key_path = package_root / 'analyst_key.json'
    manifest = read(package_root / 'manifest.json')
    if manifest['analyst_key_sha256'] != file_sha(key_path) or manifest['packet_sha256'] != sha:
        raise ValueError('analyst key or packet identity changed')
    key = read(key_path)
    identity = read(responses / 'run.json')
    if identity['packet_sha256'] != sha or identity['mode'] not in ('hf', 'mock'):
        raise ValueError('run identity mismatch')
    if identity['mode'] == 'mock' and not allow_mock:
        raise ValueError('mock outputs are not real observations')
    if identity['mode'] == 'hf':
        runtime = read(responses / 'runtime.json')
        if identity['model'] != pilot['config']['model'] or runtime['provider']['revision'] != pilot['config']['revision']:
            raise ValueError('wrong real checkpoint')
    expected = {r['request_id']: r for r in packet['requests']}
    raw = {}
    paths = sorted(responses.glob('*.response.json'))
    for path in paths:
        record = read(path)
        rid = record['request_id']
        if rid not in expected or rid in raw:
            raise ValueError('duplicate or unknown response')
        if any(record.get(k) != v for k, v in identity.items()):
            raise ValueError('mixed run identity')
        if record['record_sha256'] != digest({k: v for k, v in record.items() if k != 'record_sha256'}):
            raise ValueError('raw record changed')
        row = expected[rid]
        if any(record.get(k) != row[k] for k in ('seed', 'execution_index', 'prompt_sha256')):
            raise ValueError('prompt, order or seed changed')
        claim = read(path.with_name(path.name.replace('.response.json', '.claim.json')))
        if any(record.get(k) != v for k, v in claim.items()):
            raise ValueError('claim mismatch')
        raw[rid] = record
    bundle_ids = sorted({k['bundle_id'] for k in key.values() if k['kind'] == 'BIND'})
    values = defaultdict(lambda: [0., 0.])
    choices = defaultdict(dict)
    detail = []
    lookup = defaultdict(list)
    digits = defaultdict(Counter)
    direct = []
    valid_count = 0
    for rid, row in expected.items():
        a, r = key[rid], raw.get(rid)
        valid = r is not None and r['status'] == 'VALID' and r['raw_response'] in ('1', '2', '3') and r['failure_type'] is None
        valid_count += valid
        digit = r['raw_response'] if r else None
        item = dict(request_id=rid, kind=a['kind'], bundle_id=a['bundle_id'], layout=a['layout'],
                    status='valid' if valid else 'missing' if r is None else 'invalid', raw_output=digit)
        if a['kind'] in ('DIRECT', 'LOOKUP'):
            correct = digit == a['expected'] if valid else None
            item.update(expected=a['expected'], correct=correct)
            if a['kind'] == 'DIRECT': direct.append(correct)
            else: lookup[a['layout']].append(dict(bundle_id=a['bundle_id'], correct=correct))
        else:
            first, second = a['types']
            ds = [v[first] - v[second] for v in a['candidate_vectors']]
            span = max(ds) - min(ds)
            coefficients = [(1, -1, -1, 1)[a['cell']] * d / (2 * span) for d in ds]
            lo, hi = (coefficients[int(digit) - 1],) * 2 if valid else (min(coefficients), max(coefficients))
            value = values[(a['bundle_id'], a['layout'], a['rotation'])]
            value[0] += lo
            value[1] += hi
            index = int(digit) - 1 if valid else None
            who = (a['cell'] % 2) ^ (a['cell'] >= 2)
            probabilities = [.38 + .34 * v[a['types'][who]] for v in a['candidate_vectors']]
            item.update(cell=a['cell'], rotation=a['rotation'], candidate_order=a['candidate_order'],
                        candidate_simulator_probabilities=probabilities,
                        selected_message=a['candidate_messages'][index] if valid else None,
                        registered_vector=a['candidate_vectors'][index] if valid else None,
                        observed_new_target_choice=None)
            if valid:
                digits[a['layout']].update([digit])
                choices[(a['bundle_id'], a['layout'], a['cell'])][a['rotation']] = a['candidate_order'][index]
        detail.append(item)
    # Independently check scalar contrasts against the older vectorized engine.
    maximum_difference = 0.
    for layout in FORMATS:
        for rotation in range(3):
            typed = np.zeros((36, 2), dtype=int)
            vectors = np.zeros((36, 6, 3, 3))
            selected = np.full((1, 36, 6, 4), -1, dtype=int)
            for i, bid in enumerate(bundle_ids):
                for cell in range(4):
                    rid = f'{bid}/BIND/{layout}/{rotation}/{cell}'
                    a, r = key[rid], raw.get(rid)
                    typed[i] = a['types']
                    vectors[i, :] = np.array(a['candidate_vectors'])
                    if r and r['status'] == 'VALID' and r['raw_response'] in ('1', '2', '3') and r['failure_type'] is None:
                        selected[0, i, 0, cell] = int(r['raw_response']) - 1
            lo, hi = bounds_from_choices(typed, vectors, selected)
            for i, bid in enumerate(bundle_ids):
                target = values[(bid, layout, rotation)]
                maximum_difference = max(maximum_difference, abs(lo[0, i, 0] - target[0]), abs(hi[0, i, 0] - target[1]))
    if maximum_difference > 1e-12:
        raise ValueError('independent contrast calculation disagrees')
    by_bundle = {}
    for bid in bundle_ids:
        by_bundle[bid] = {layout: [statistics.mean(values[(bid, layout, r)][side] for r in range(3))
                                  for side in (0, 1)] for layout in FORMATS}
    aggregates = {layout: dict(lower=stats([by_bundle[b][layout][0] for b in bundle_ids]),
                               upper=stats([by_bundle[b][layout][1] for b in bundle_ids])) for layout in FORMATS}
    paired = [[by_bundle[b]['compact'][0] - by_bundle[b]['prose'][1],
               by_bundle[b]['compact'][1] - by_bundle[b]['prose'][0]] for b in bundle_ids]
    stable = {layout: dict(complete_cells=sum(len(v) == 3 for (b, f, c), v in choices.items() if f == layout),
                           same_semantic_choice_all_rotations=sum(len(v) == 3 and len(set(v.values())) == 1
                                                                  for (b, f, c), v in choices.items() if f == layout),
                           planned_cells=144) for layout in FORMATS}
    control_counts = lambda vals: dict(planned=len(vals), correct=sum(v is True for v in vals),
                                      wrong=sum(v is False for v in vals), missing_or_invalid=sum(v is None for v in vals))
    summary = dict(status='MOCK_NOT_SCIENTIFIC' if identity['mode'] == 'mock' else 'EXPLORATORY_PRESENTATION_DIAGNOSTIC',
                   model=identity['model'], revision=pilot['config']['revision'], packet_sha256=sha,
                   collected=len(raw), planned=972, valid=valid_count,
                   direct=control_counts(direct), lookup={f: control_counts([v['correct'] for v in lookup[f]]) for f in FORMATS},
                   binding=aggregates, paired_compact_minus_prose=dict(lower=stats([v[0] for v in paired]), upper=stats([v[1] for v in paired])),
                   paired_lookup=lookup, bundle_bounds=by_bundle,
                   rotation_bounds={f'{b}/{f}/{r}': v for (b, f, r), v in values.items()},
                   digits={f: dict(c) for f, c in digits.items()}, semantic_stability=stable,
                   independent_score_max_difference=maximum_difference, requests=detail,
                   confidence_intervals=None, p_values=None, latent_model_demonstrated=False)
    output.mkdir(parents=True, exist_ok=False)
    write_new(output / 'summary.json', summary)
    lines = ['# Presentation diagnostic: complete descriptive record', '',
             f"Status: {summary['status']}. Model: {summary['model']}. Valid requests: {valid_count}/972.",
             'The same 36 existing bundles are used. This is not a new confirmatory sample.', '',
             f"Direct controls: {summary['direct']}", f"Lookup controls: {summary['lookup']}", '',
             '| Layout | Mean lower bound | Mean upper bound | Sample SD of lower bounds |',
             '| --- | ---: | ---: | ---: |']
    for layout in FORMATS:
        a = aggregates[layout]
        lines.append(f"| {layout} | {a['lower']['mean']:.6f} | {a['upper']['mean']:.6f} | {a['lower']['sample_sd']:.6f} |")
    lines.extend(['', 'These are normalized binding contrasts, not success rates or evidence of a unique latent mechanism.',
                  'Missing cells remain in bounds. A range here is not a confidence interval.', '', '## Every bundle', '',
                  '| Bundle | Prose bounds | Compact bounds | Compact minus prose bounds |', '| --- | --- | --- | --- |'])
    for bid, pair in zip(bundle_ids, paired):
        lines.append(f"| {bid} | {by_bundle[bid]['prose']} | {by_bundle[bid]['compact']} | {pair} |")
    lines.extend(['', '## Every raw response', ''])
    for item in detail:
        lines.extend(['### ' + item['request_id'], '', f"Status: {item['status']}. Raw output: {item['raw_output']!r}."])
        if item['kind'] == 'BIND':
            lines.extend([f"Selected message: {item['selected_message']}",
                          f"Registered vector: {item['registered_vector']}",
                          f"Candidate P(A): {item['candidate_simulator_probabilities']}. No new target choice was sampled.", ''])
        else:
            lines.extend([f"Expected: {item['expected']}. Correct: {item['correct']}.", ''])
    (output / 'REPORT.md').write_text('\n'.join(lines) + '\n')
    write_new(output / 'manifest.json', dict(inputs={str(p): file_sha(p) for p in [*paths, key_path, package_root / 'manifest.json', Path(__file__)]},
                                             outputs={p.name: file_sha(p) for p in output.iterdir() if p.is_file()}))
    return {k: summary[k] for k in ('status', 'collected', 'valid', 'direct', 'lookup', 'binding', 'paired_compact_minus_prose')}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('package', 'responses', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--allow-mock', action='store_true')
    a = p.parse_args()
    print(analyze(a.package, a.responses, a.output, a.allow_mock))
