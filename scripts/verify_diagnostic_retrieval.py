"""Verify the scoped result archive before extracting and acknowledging backup."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile


def verify(archive, destination, expected_sha,
           expected_pod='cgy7iwpf6z74qr',
           expected_packet='418f24b657eff7bb731ddb93a066889c63507fcab5cadc414231c3257ecba4f1'):
    archive, destination = Path(archive), Path(destination)
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    if actual != expected_sha:
        raise ValueError('archive hash mismatch')
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        names = [m.name for m in members]
        if len(set(names)) != len(names):
            raise ValueError('duplicate archive path')
        for member in members:
            path = PurePosixPath(member.name)
            if not member.isfile() or path.is_absolute() or '..' in path.parts:
                raise ValueError('unsafe archive member')
        manifest = json.load(tar.extractfile('retrieval_manifest.json'))
        if manifest['pod_id'] != expected_pod:
            raise ValueError('wrong pod')
        if manifest['packet_sha256'] != expected_packet:
            raise ValueError('wrong packet')
        if set(names) != set(manifest['files']) | {'retrieval_manifest.json'}:
            raise ValueError('incomplete manifest')
        for name, expected in manifest['files'].items():
            if hashlib.sha256(tar.extractfile(name).read()).hexdigest() != expected:
                raise ValueError('file hash mismatch: ' + name)
        destination.mkdir(exist_ok=False)
        tar.extractall(destination, filter='data')
    for name, expected in manifest['files'].items():
        if hashlib.sha256((destination / name).read_bytes()).hexdigest() != expected:
            raise ValueError('extracted hash mismatch: ' + name)
    count = len(list((destination / 'responses').glob('*.response.json')))
    if count != manifest['responses_present']:
        raise ValueError('response count mismatch')
    receipt = {
        'status': 'BACKUP_VERIFIED', 'verified_utc': datetime.now(timezone.utc).isoformat(),
        'pod_id': manifest['pod_id'], 'packet_sha256': manifest['packet_sha256'],
        'archive_sha256': actual, 'files_verified': len(manifest['files']),
        'responses_present': count, 'archive_bytes': archive.stat().st_size,
    }
    with (destination.parent / 'backup_receipt.json').open('x') as file:
        json.dump(receipt, file, indent=2)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--pod-id', default='cgy7iwpf6z74qr')
    parser.add_argument('--packet-sha256', default='418f24b657eff7bb731ddb93a066889c63507fcab5cadc414231c3257ecba4f1')
    args = parser.parse_args()
    print(json.dumps(verify(args.archive, args.destination, args.sha256, args.pod_id, args.packet_sha256)))
