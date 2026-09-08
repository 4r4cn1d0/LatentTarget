"""Freeze a presentation diagnostic, including its analyst key and exact source hashes."""
import argparse
from pathlib import Path
import shutil
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_diagnostic_packet import rows
from src.diagnostic_pilot import read, write_new, digest, file_sha, verify_package
from src.grounded_partner import grounded_integrity
from src.presentation_diagnostic import build_requests, validate, N_REQUESTS


def build(source, pilot_root, output):
    manifest = read(source / 'manifest.json')
    for name, sha in manifest['outputs'].items():
        if not (source / name).resolve().is_relative_to(source.resolve()) or file_sha(source / name) != sha:
            raise ValueError('fixed input changed')
    verify_package(pilot_root / 'package')
    pilot = read(pilot_root / 'package/packet.json')
    plan, bank = read(source / 'design_snapshot.json'), read(source / 'bank_snapshot.json')
    bundles, ledger = rows(source / 'evaluation/bundles.jsonl.gz'), rows(source / 'evaluation/ledger.jsonl.gz')
    grounded_integrity(plan, bank, bundles, ledger)
    requests, key = build_requests(plan, bank, bundles)
    packet = dict(id='presentation_diagnostic_20260909', model_config=pilot['config'], maximum_requests=N_REQUESTS,
                  requests=requests, source_manifest_sha256=file_sha(source / 'manifest.json'),
                  plan_sha256=file_sha(ROOT / 'docs/PRESENTATION_DIAGNOSTIC_PLAN_20260909.md'),
                  analysis_status='EXPLORATORY_PRESENTATION_DIAGNOSTIC_NOT_LATENT_CONFIRMATION')
    packet_sha = validate(packet, pilot)
    output.mkdir(parents=True, exist_ok=False)
    package = output / 'package'
    for path in (pilot_root / 'package').rglob('*'):
        if path.is_file() and path.name != 'package_manifest.json':
            dest = package / path.relative_to(pilot_root / 'package')
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest)
    for name in ('src/presentation_diagnostic.py', 'src/presentation_collection.py',
                 'scripts/run_presentation_diagnostic.py'):
        shutil.copyfile(ROOT / name, package / name)
    write_new(package / 'presentation_packet.json', packet)
    write_new(output / 'analyst_key.json', key)
    write_new(package / 'package_manifest.json', dict(packet_sha256=packet_sha,
              files={str(p.relative_to(package)): file_sha(p) for p in package.rglob('*') if p.is_file()}))
    verify_package(package)
    archive = output / 'presentation_diagnostic.tar.gz'
    with tarfile.open(archive, 'x:gz') as tar:
        tar.add(package, arcname='package')
    result = dict(status='PACKAGED_NOT_RUN', maximum_requests=N_REQUESTS, packet_sha256=packet_sha,
                  archive_sha256=file_sha(archive), analyst_key_sha256=file_sha(output / 'analyst_key.json'))
    write_new(output / 'manifest.json', result)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'pilot', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    args = p.parse_args()
    print(build(args.source, args.pilot, args.output))
