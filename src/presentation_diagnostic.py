"""Lossless presentation intervention on the fixed history bank, not a new latent test."""
from copy import deepcopy
import json
import random

from src.diagnostic_pilot import digest, validate_packet

FORMATS = ('prose', 'compact')
N_REQUESTS = 972
SEED = 202609091


def visible_events(bundle, rebound=False):
    exchange = dict(zip(bundle['aliases'], reversed(bundle['aliases'])))
    return [dict(record=i, participant=exchange[e['participant']] if rebound else e['participant'],
                 decision=e['decision'], option_a=e['option_a'], option_b=e['option_b'],
                 message=e['message'], choice=e['choice'])
            for i, e in enumerate(bundle['events'], 1)]


def compact_data(events):
    scenarios = []
    records = []
    for event in events:
        scenario = {k: event[k] for k in ('decision', 'option_a', 'option_b')}
        if scenario not in scenarios:
            scenarios.append(scenario)
        records.append(dict(record=event['record'], participant=event['participant'],
                            scenario_id=scenarios.index(scenario) + 1,
                            message=event['message'], choice=event['choice']))
    return dict(scenarios=scenarios, records=records)


def expand_compact(data):
    return [dict(record=r['record'], participant=r['participant'],
                 **data['scenarios'][r['scenario_id'] - 1], message=r['message'], choice=r['choice'])
            for r in data['records']]


def history_text(events, layout):
    if layout == 'prose':
        lines = ['Records of earlier interactions:']
        for e in events:
            lines.extend(['', f"Record {e['record']}", f"Participant: {e['participant']}",
                          f"Decision: {e['decision']}", f"Option A: {e['option_a']}",
                          f"Option B: {e['option_b']}", f"Message: {e['message']}",
                          f"Choice: Option {e['choice']}"])
        return '\n'.join(lines)
    if layout != 'compact':
        raise ValueError('unknown history layout')
    data = compact_data(events)
    if expand_compact(data) != events:
        raise ValueError('compaction changed evidence')
    lines = ['Records of earlier interactions:',
             'Each scenario below is stated once. Record rows refer to its numbered scenario.',
             'A choice of A means Option A; B means Option B.', '', 'Scenarios:']
    for i, scenario in enumerate(data['scenarios'], 1):
        lines.extend([f'Scenario {i}', f"Decision: {scenario['decision']}",
                      f"Option A: {scenario['option_a']}", f"Option B: {scenario['option_b']}"])
    lines.extend(['', 'Records (one JSON object per row):'])
    lines.extend(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in data['records'])
    return '\n'.join(lines)


def choice_prompt(plan, bank, bundle, cell, layout, rotation):
    from src.grounded_partner import grounded_candidates, grounded_prompt
    b = deepcopy(bundle)
    order = b['candidate_order']
    b['candidate_order'] = order[rotation:] + order[:rotation]
    spec = dict(branch='BIND', bank='familiar', cell=cell, recipient=cell % 2, rebound=cell >= 2)
    original = grounded_prompt(plan, bank, b, spec)
    before, marker, tail = original['user'].partition('\n\n' + plan['prompts']['history_end'] + '\n\n')
    events = visible_events(bundle, cell >= 2)
    if before != history_text(events, 'prose') or not marker:
        raise ValueError('original evidence rendering changed')
    prompt = dict(system=original['system'], user=history_text(events, layout) + marker + tail)
    texts, vectors = grounded_candidates(bank, b, spec)
    return prompt, texts, vectors, b['candidate_order']


def build_requests(plan, bank, bundles):
    if len(bundles) != 36 or len({b['bundle_id'] for b in bundles}) != 36:
        raise ValueError('all 36 fixed bundles required')
    requests, key = [], {}

    def add(rid, kind, bundle_id, layout, rotation, cell, seed, prompt, answer=None, **analyst):
        row = dict(request_id=rid, kind=kind, bundle_id=bundle_id, layout=layout,
                   rotation=rotation, cell=cell, seed=seed, prompt=prompt,
                   prompt_sha256=digest(prompt), direct_answer=answer)
        requests.append(row)
        key[rid] = dict(kind=kind, bundle_id=bundle_id, layout=layout, rotation=rotation,
                        cell=cell, **analyst)

    for i in range(36):
        answer = str(i % 3 + 1)
        prompt = dict(system='Follow the requested output format exactly.',
                      user=f'Output format check {i + 1}. Reply with exactly the digit {answer}. Do not include any other text.')
        add(f'direct/{i:02d}', 'DIRECT', None, None, None, None,
            int(digest([SEED, 'direct', i])[:8], 16), prompt, answer=answer, expected=answer)
    rest = []
    for b in bundles:
        for layout in FORMATS:
            for rotation in range(3):
                for cell in range(4):
                    prompt, texts, vectors, order = choice_prompt(plan, bank, b, cell, layout, rotation)
                    rid = f"{b['bundle_id']}/BIND/{layout}/{rotation}/{cell}"
                    add(rid, 'BIND', b['bundle_id'], layout, rotation, cell,
                        int(digest([SEED, b['bundle_id'], 'BIND', cell])[:8], 16), prompt,
                        types=b['types'], candidate_messages=texts, candidate_vectors=vectors,
                        candidate_order=order, family=b['grounded_family'])
                    rest.append(requests.pop())
            events = visible_events(b)
            index = 8 + int(digest([SEED, b['bundle_id'], 'lookup'])[:8], 16) % 8
            event = events[index]
            prompt = dict(system='Answer the factual question using only the supplied records. Follow the requested output format.',
                          user=history_text(events, layout) +
                          f"\n\nEnd of records.\nWhat choice is recorded in Record {event['record']}?\n"
                          'Reply with exactly one digit: 1 for Option A, 2 for Option B, or 3 if no choice is recorded.')
            add(f"{b['bundle_id']}/LOOKUP/{layout}", 'LOOKUP', b['bundle_id'], layout, None, None,
                int(digest([SEED, b['bundle_id'], 'LOOKUP'])[:8], 16), prompt,
                expected='1' if event['choice'] == 'A' else '2', record_number=event['record'])
            rest.append(requests.pop())
    random.Random(SEED).shuffle(rest)
    requests.extend(rest)
    for i, row in enumerate(requests):
        row['execution_index'] = i
    return requests, key


def validate(packet, pilot):
    validate_packet(pilot)
    if packet['model_config'] != pilot['config'] or packet['maximum_requests'] != N_REQUESTS:
        raise ValueError('model or request limit changed')
    rows = packet['requests']
    if len(rows) != N_REQUESTS or len({r['request_id'] for r in rows}) != N_REQUESTS:
        raise ValueError('incomplete or duplicate schedule')
    from collections import Counter
    if Counter(r['kind'] for r in rows) != dict(DIRECT=36, BIND=864, LOOKUP=72):
        raise ValueError('wrong allocation')
    if any(r['kind'] != 'DIRECT' for r in rows[:36]) or any(r['kind'] == 'DIRECT' for r in rows[36:]):
        raise ValueError('direct checks must precede the study')
    for i, row in enumerate(rows):
        if row['execution_index'] != i or set(row['prompt']) != {'system', 'user'} or row['prompt_sha256'] != digest(row['prompt']):
            raise ValueError('execution or prompt identity changed')
        if row['kind'] == 'DIRECT' and row['direct_answer'] != str(i % 3 + 1):
            raise ValueError('direct answer changed')
        if row['kind'] != 'DIRECT' and row['direct_answer'] is not None:
            raise ValueError('analyst answer cannot enter focal calls')
        if row['kind'] == 'DIRECT':
            expected_seed = int(digest([SEED, 'direct', i])[:8], 16)
        elif row['kind'] == 'BIND':
            if row['layout'] not in FORMATS or row['rotation'] not in range(3) or row['cell'] not in range(4):
                raise ValueError('invalid binding cell')
            if row['request_id'] != f"{row['bundle_id']}/BIND/{row['layout']}/{row['rotation']}/{row['cell']}":
                raise ValueError('binding request identity changed')
            expected_seed = int(digest([SEED, row['bundle_id'], 'BIND', row['cell']])[:8], 16)
        else:
            if row['layout'] not in FORMATS or row['rotation'] is not None or row['cell'] is not None:
                raise ValueError('invalid lookup cell')
            if row['request_id'] != f"{row['bundle_id']}/LOOKUP/{row['layout']}":
                raise ValueError('lookup request identity changed')
            expected_seed = int(digest([SEED, row['bundle_id'], 'LOOKUP'])[:8], 16)
        if row['seed'] != expected_seed:
            raise ValueError('paired seed changed')
    bundle_ids = {r['bundle_id'] for r in rows if r['kind'] == 'BIND'}
    if len(bundle_ids) != 36 or Counter(r['bundle_id'] for r in rows if r['kind'] == 'BIND') != {b: 24 for b in bundle_ids}:
        raise ValueError('bundle allocation changed')
    if Counter(r['bundle_id'] for r in rows if r['kind'] == 'LOOKUP') != {b: 2 for b in bundle_ids}:
        raise ValueError('lookup allocation changed')
    return digest(packet)
