import hashlib
import io
import json
import tarfile

import pytest
from scripts.verify_diagnostic_retrieval import verify


def fixture_archive(tmp_path, corrupt=False, unsafe=False):
    payload = b'{"fixture":true}'
    name = 'responses/000.response.json'
    manifest = {'pod_id': 'cgy7iwpf6z74qr', 'responses_present': 1,
                'packet_sha256': '418f24b657eff7bb731ddb93a066889c63507fcab5cadc414231c3257ecba4f1',
                'files': {name: 'incorrect' if corrupt else hashlib.sha256(payload).hexdigest()}}
    archive = tmp_path / 'fixture.tar.gz'
    with tarfile.open(archive, 'w:gz') as tar:
        for n, data in [(name, payload), ('retrieval_manifest.json', json.dumps(manifest).encode())]:
            info = tarfile.TarInfo(n); info.size = len(data); tar.addfile(info, io.BytesIO(data))
        if unsafe:
            info = tarfile.TarInfo('../escape'); info.size = 0; tar.addfile(info, io.BytesIO(b''))
    return archive, hashlib.sha256(archive.read_bytes()).hexdigest()


def test_verified_backup_and_exclusive_destination(tmp_path):
    archive, sha = fixture_archive(tmp_path)
    dest = tmp_path / 'retrieved'
    result = verify(archive, dest, sha)
    assert result['responses_present'] == 1 and result['files_verified'] == 1
    assert (tmp_path / 'backup_receipt.json').exists()
    with pytest.raises(FileExistsError):
        verify(archive, dest, sha)


@pytest.mark.parametrize('failure', ['archive_hash', 'file_hash', 'unsafe_path'])
def test_bad_archive_rejected_before_extraction(tmp_path, failure):
    archive, sha = fixture_archive(tmp_path, failure == 'file_hash', failure == 'unsafe_path')
    dest = tmp_path / 'retrieved'
    with pytest.raises(ValueError):
        verify(archive, dest, 'incorrect' if failure == 'archive_hash' else sha)
    assert not dest.exists()
