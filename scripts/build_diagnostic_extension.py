"""Package the 660 uncollected requests from the existing 720 choice bank."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tarfile

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.build_diagnostic_packet import rows
from src.diagnostic_pilot import read,write_new,file_sha,digest,validate_packet,verify_package
from src.diagnostic_extension import validate_extension
from src.grounded_partner import grounded_integrity


def build(source,pilot_dir,prior_responses,output):
    manifest=read(source/'manifest.json')
    for name,sha in manifest['outputs'].items():
        if not (source/name).resolve().is_relative_to(source.resolve()) or file_sha(source/name)!=sha:
            raise ValueError('frozen source changed')
    verify_package(pilot_dir/'package')
    pilot=read(pilot_dir/'package/packet.json');sha=validate_packet(pilot)
    bundles=rows(source/'evaluation/bundles.jsonl.gz');ledger=rows(source/'evaluation/ledger.jsonl.gz')
    grounded_integrity(read(source/'design_snapshot.json'),read(source/'bank_snapshot.json'),bundles,ledger)
    if len(bundles)!=36:raise ValueError('requires all 36 fixed bundles')
    previous={r['request_id']:r for r in pilot['requests']}
    completed={}
    for path in sorted(prior_responses.glob('*.response.json')):
        row=read(path);rid=row['request_id']
        if rid in completed or rid not in previous:raise ValueError('prior response identity mismatch')
        if (row['record_sha256']!=digest({k:v for k,v in row.items() if k!='record_sha256'})
            or row['packet_sha256']!=sha or row['prompt_sha256']!=previous[rid]['prompt_sha256']
            or row['seed']!=previous[rid]['seed'] or row['status']!='VALID' or row['mode']!='hf'):
            raise ValueError('unverified prior result')
        completed[rid]={'file_sha256':file_sha(path),'record_sha256':row['record_sha256'],'filename':path.name}
    if set(completed)!=set(previous):raise ValueError('pilot responses incomplete')
    requests=[]
    for row in ledger:
        if row['spec']['branch']=='FORECAST':continue
        if row['request_id'] in previous:
            if row['prompt']!=previous[row['request_id']]['prompt']:raise ValueError('pilot prompt changed')
            continue
        requests.append(dict(row,execution_index=len(requests),seed=int(digest([202609089,row['request_id']])[:8],16)))
    packet={'id':'fixed_bank_extension_20260909','pilot_packet_sha256':sha,'model_config':pilot['config'],
            'new_requests':660,'combined_requests':720,'requests':requests,
            'prior_results':completed,'source_manifest_sha256':file_sha(source/'manifest.json'),
            'source_ledger_sha256':file_sha(source/'evaluation/ledger.jsonl.gz'),
            'analysis_status':'descriptive_followup_after_pilot_not_confirmation'}
    extension_sha=validate_extension(packet,pilot)
    output.mkdir(parents=True,exist_ok=False);package=output/'package';package.mkdir()
    for path in (pilot_dir/'package').rglob('*'):
        if path.is_file() and path.name!='package_manifest.json':
            dest=package/path.relative_to(pilot_dir/'package');dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,dest)
    for name in ('src/diagnostic_extension.py','scripts/run_diagnostic_extension.py'):
        shutil.copyfile(ROOT/name,package/name)
    write_new(package/'extension_packet.json',packet)
    files={str(p.relative_to(package)):file_sha(p) for p in package.rglob('*') if p.is_file()}
    write_new(package/'package_manifest.json',{'packet_sha256':extension_sha,'files':files})
    verify_package(package)
    archive=output/'diagnostic_extension.tar.gz'
    with tarfile.open(archive,'x:gz') as tar:tar.add(package,arcname='package')
    result={'status':'PACKAGED_NOT_RUN','new_requests':660,'existing_requests':60,'combined_bundles':36,
            'packet_sha256':extension_sha,'archive_sha256':file_sha(archive),
            'maximum_total_usd_including_pilot':5,'maximum_restart_seconds':5400,
            'reuse_prior_results_without_regeneration':True,'no_new_histories':True,
            'no_prompt_or_model_change':True,'no_activation_capture':True}
    write_new(output/'manifest.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--pilot',type=Path,required=True)
    parser.add_argument('--prior-responses',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(build(args.source,args.pilot,args.prior_responses,args.output)))
