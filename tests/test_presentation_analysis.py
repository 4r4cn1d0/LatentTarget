"""Only explicitly marked mock fixtures enter these local analyzer tests."""
from pathlib import Path
import shutil
import pytest
from scripts.analyze_presentation_diagnostic import analyze
from src.diagnostic_pilot import read, write_new, digest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'results/presentation_package_20260909'
MOCK = ROOT / 'results/presentation_mock_20260909'


def test_mock_requires_explicit_opt_in(tmp_path):
    with pytest.raises(ValueError, match='mock'):
        analyze(PACKAGE, MOCK, tmp_path / 'report')
    assert not (tmp_path / 'report').exists()


@pytest.mark.parametrize('invalid', [False, True])
def test_missing_and_invalid_remain_bounded(tmp_path, invalid):
    out = tmp_path / 'mock_fixture'
    out.mkdir()
    shutil.copyfile(MOCK / 'run.json', out / 'run.json')
    packet = read(PACKAGE / 'package/presentation_packet.json')
    request = next(r for r in packet['requests'] if r['kind'] == 'BIND')
    name = f"{request['execution_index']:04d}"
    shutil.copyfile(MOCK / f'{name}.claim.json', out / f'{name}.claim.json')
    row = read(MOCK / f'{name}.response.json')
    if invalid:
        row['raw_response'] = '1 '
        row['status'] = 'INVALID_OR_FAILED'
        row['record_sha256'] = digest({k: v for k, v in row.items() if k != 'record_sha256'})
    write_new(out / f'{name}.response.json', row)
    result = analyze(PACKAGE, out, tmp_path / 'report', allow_mock=True)
    assert result['valid'] == (0 if invalid else 1)
    report = read(tmp_path / 'report/summary.json')
    assert len(report['requests']) == 972 and report['independent_score_max_difference'] < 1e-12
    for layout in ('prose', 'compact'):
        assert report['binding'][layout]['lower']['mean'] < report['binding'][layout]['upper']['mean']
    if invalid:
        assert report['binding']['prose']['lower']['mean'] == -1
        assert report['binding']['prose']['upper']['mean'] == 1
