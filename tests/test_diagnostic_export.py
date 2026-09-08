import json
from pathlib import Path
import tarfile
from types import SimpleNamespace

import pytest

from scripts.export_diagnostic_run import export,sha


def test_complete_allowlist_export_and_cache_exclusion(tmp_path,monkeypatch):
    root=tmp_path/'latenttarget-diagnostic-20260909';root.mkdir()
    (root/'approval.json').write_text(json.dumps({'pod_id':'fixture-pod','packet_sha256':'fixture-sha','maximum_requests':60}))
    (root/'bootstrap.log').write_text('fixture log')
    for name in ('package','responses','hf-cache','runtime'):(root/name).mkdir()
    (root/'package/packet.json').write_text('{}')
    for i in range(3):(root/'responses'/f'{i:03d}.response.json').write_text('{}')
    (root/'hf-cache/weights').write_text('excluded')
    (root/'runtime/library').write_text('excluded')
    monkeypatch.setattr('scripts.export_diagnostic_run.subprocess.run',lambda *a,**k:SimpleNamespace(stdout='torch==2.9.1\n'))
    result=export(root)
    assert result['responses_present']==3
    with tarfile.open(result['archive']) as t:
        names=t.getnames()
        assert not any(n.startswith(('hf-cache/','runtime/')) for n in names)
        assert len([n for n in names if n.endswith('.response.json')])==3
        manifest=json.load(t.extractfile('retrieval_manifest.json'))
        for name,h in manifest['files'].items():assert h==sha(root/name)


def test_unexpected_scope_rejected(tmp_path):
    with pytest.raises(ValueError):export(tmp_path)


def test_extension_scope_and_filename(tmp_path,monkeypatch):
    root=tmp_path/'latenttarget-extension-20260909';root.mkdir()
    (root/'approval.json').write_text(json.dumps({'pod_id':'extension-pod','packet_sha256':'extension-sha','maximum_requests':660}))
    (root/'bootstrap_diagnostic_extension.sh').write_text('fixture')
    (root/'diagnostic_extension.tar.gz').write_bytes(b'fixture')
    (root/'responses').mkdir()
    monkeypatch.setattr('scripts.export_diagnostic_run.subprocess.run',lambda *a,**k:SimpleNamespace(stdout='torch==2.9.1\n'))
    result=export(root)
    with tarfile.open(result['archive']) as t:
        assert 'bootstrap_diagnostic_extension.sh' in t.getnames()
        assert 'diagnostic_extension.tar.gz' in t.getnames()


def test_presentation_reuses_runtime_but_exports_only_its_own_results(tmp_path, monkeypatch):
    root = tmp_path / 'latenttarget-presentation-20260909'
    root.mkdir()
    (root / 'approval.json').write_text(json.dumps({'pod_id': 'presentation-fixture', 'packet_sha256': 'fixture', 'maximum_requests': 972}))
    (root / 'bootstrap_presentation_diagnostic.sh').write_text('fixture')
    (root / 'presentation_diagnostic.tar.gz').write_bytes(b'fixture')
    seen = []
    def freeze(args, **kwargs):
        seen.append(args[0])
        return SimpleNamespace(stdout='torch==2.9.1\n')
    monkeypatch.setattr('scripts.export_diagnostic_run.subprocess.run', freeze)
    result = export(root)
    assert seen == [str(tmp_path / 'latenttarget-extension-20260909/runtime/bin/python')]
    with tarfile.open(result['archive']) as t:
        assert 'presentation_diagnostic.tar.gz' in t.getnames()
        assert 'bootstrap_presentation_diagnostic.sh' in t.getnames()
