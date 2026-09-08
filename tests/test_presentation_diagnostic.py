from collections import Counter
from copy import deepcopy
from pathlib import Path
import pytest

from scripts.build_diagnostic_packet import rows
from src.diagnostic_pilot import read
from src.presentation_diagnostic import (build_requests, visible_events, compact_data, expand_compact,
                                         choice_prompt, validate)
from src.presentation_collection import collect, approval_check

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'results/grounded_partner_readiness_20260908'


@pytest.fixture(scope='module')
def materials():
    plan, bank = read(SOURCE / 'design_snapshot.json'), read(SOURCE / 'bank_snapshot.json')
    bundles = rows(SOURCE / 'evaluation/bundles.jsonl.gz')
    requests, key = build_requests(plan, bank, bundles)
    pilot = read(ROOT / 'results/diagnostic_pilot_package_20260908/package/packet.json')
    return plan, bank, bundles, dict(model_config=pilot['config'], maximum_requests=972, requests=requests), key, pilot


def test_every_visible_event_reconstructs_and_analyst_metadata_excluded(materials):
    _, _, bundles, _, _, _ = materials
    for b in bundles:
        for rebound in (False, True):
            events = visible_events(b, rebound)
            assert len(events) == 24 and expand_compact(compact_data(events)) == events
            assert all(not any(k.startswith('analyst') for k in e) for e in events)


def test_exact_prose_and_every_candidate_position(materials):
    from src.grounded_partner import grounded_prompt
    plan, bank, bundles, _, _, _ = materials
    for b in bundles:
        for cell in range(4):
            p, _, _, _ = choice_prompt(plan, bank, b, cell, 'prose', 0)
            assert p == grounded_prompt(plan, bank, b, dict(branch='BIND', bank='familiar',
                      cell=cell, recipient=cell % 2, rebound=cell >= 2))
            orders = [choice_prompt(plan, bank, b, cell, 'compact', r)[3] for r in range(3)]
            for position in range(3):
                assert {o[position] for o in orders} == {0, 1, 2}


def test_exact_allocation_and_paired_seeds(materials):
    _, _, _, packet, key, pilot = materials
    validate(packet, pilot)
    assert Counter(r['kind'] for r in packet['requests']) == dict(DIRECT=36, BIND=864, LOOKUP=72)
    assert len(key) == 972
    assert Counter(r['direct_answer'] for r in packet['requests'][:36]) == {'1': 12, '2': 12, '3': 12}


@pytest.mark.parametrize('change', ['seed', 'prompt', 'model', 'duplicate'])
def test_tampering_rejected(materials, change):
    packet, pilot = deepcopy(materials[3]), materials[5]
    if change == 'seed': packet['requests'][40]['seed'] += 1
    elif change == 'prompt': packet['requests'][40]['prompt']['user'] += 'changed'
    elif change == 'model': packet['model_config']['generation']['temperature'] = 0
    else: packet['requests'][40]['request_id'] = packet['requests'][41]['request_id']
    with pytest.raises(ValueError): validate(packet, pilot)


def test_mock_full_collection_and_no_overwrite(materials, tmp_path):
    result = collect(materials[3], materials[5], tmp_path / 'mock')
    assert result['responses'] == 972 and result['mode'] == 'mock'
    with pytest.raises(FileExistsError): collect(materials[3], materials[5], tmp_path / 'mock')


def test_provider_sees_only_prompt_and_failure_is_retained(materials, tmp_path):
    class Failed:
        def set_next_seed(self, seed): pass
        def generate(self, prompt):
            assert not prompt.context
            raise RuntimeError('test fixture')
    with pytest.raises(RuntimeError, match='retained'):
        collect(materials[3], materials[5], tmp_path / 'failed', provider_factory=Failed)
    record = read(tmp_path / 'failed/0000.response.json')
    assert record['failure_type'] == 'RuntimeError' and record['raw_response'] is None


def test_missing_approval_prevents_real_collection(materials, tmp_path):
    with pytest.raises(ValueError, match='approval'):
        collect(materials[3], materials[5], tmp_path / 'forbidden', mode='hf')
    assert not (tmp_path / 'forbidden').exists()


def test_direct_failure_stops_before_focal_calls(materials, tmp_path, monkeypatch):
    # A simulated provider lives only in this temporary test fixture.
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace
    class Simulated:
        capture = False
        _model = SimpleNamespace(generation_config=SimpleNamespace())
        _tok = SimpleNamespace(decode=lambda seq: str(seq[0]))
        def _format_inputs(self, system, user):
            return {'input_ids': SimpleNamespace(shape=(1, 40))}
        def set_next_seed(self, seed): pass
        def generate(self, prompt): return '1'
    monkeypatch.setattr('src.presentation_collection.real_provider', lambda *a: Simulated())
    monkeypatch.setattr('src.hf_provider._choice_token_sequences', lambda *a: ((1,), (2,), (3,)))
    sha = validate(materials[3], materials[5])
    approval = dict(approved=True, packet_sha256=sha, maximum_requests=972, maximum_total_usd=5,
                    watchdog_verified=True, pod_id='synthetic-fixture', hourly_quote_usd=1.59,
                    pod_deadline_utc=(datetime.now(timezone.utc) + timedelta(minutes=89)).isoformat())
    result = collect(materials[3], materials[5], tmp_path / 'simulated', mode='hf', approval=approval)
    assert result['status'] == 'DIRECT_CONTROL_FAILED' and result['responses'] == 36
    assert result['direct_correct'] == 12
    assert len(list((tmp_path / 'simulated').glob('*.response.json'))) == 36
