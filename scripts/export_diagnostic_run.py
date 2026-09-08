"""Archive every diagnostic result and its inputs, excluding model/runtime cache."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def export(root):
    root=Path(root).resolve()
    scopes={'latenttarget-diagnostic-20260909':60,'latenttarget-extension-20260909':660,
            'latenttarget-presentation-20260909':972}
    if root.name not in scopes:raise ValueError('unexpected run directory')
    approval=json.loads((root/'approval.json').read_text())
    if approval['maximum_requests']!=scopes[root.name]:raise ValueError('unexpected run scope')
    runtime=root/'runtime/bin/python'
    if root.name=='latenttarget-presentation-20260909' and not runtime.exists():
        runtime=root.parent/'latenttarget-extension-20260909/runtime/bin/python'
    freeze=subprocess.run([str(runtime),'-m','pip','freeze'],text=True,capture_output=True,check=True)
    with (root/'runtime_packages.txt').open('x') as f:f.write(freeze.stdout)
    fixed=['approval.json','bootstrap.log','bootstrap_diagnostic_gpu.sh','runtime_packages.txt',
           'hardware_preflight.json','latenttarget_diagnostic_20260908.tar.gz',
           'bootstrap_diagnostic_extension.sh','diagnostic_extension.tar.gz',
           'bootstrap_presentation_diagnostic.sh','presentation_diagnostic.tar.gz']
    files=[root/name for name in fixed if (root/name).is_file()]
    for directory in ('package','responses'):
        p=root/directory
        if p.exists():files.extend(sorted(f for f in p.rglob('*') if f.is_file()))
    if any(f.is_symlink() or not f.resolve().is_relative_to(root) for f in files):raise ValueError('unexpected archive path')
    manifest={'pod_id':approval['pod_id'],'packet_sha256':approval['packet_sha256'],
              'responses_present':len(list((root/'responses').glob('*.response.json'))),
              'files':{str(f.relative_to(root)):sha(f) for f in files},
              'excluded':['runtime virtual environment','downloaded public model weights'],
              'all_raw_responses_included':True}
    with (root/'retrieval_manifest.json').open('x') as f:json.dump(manifest,f,indent=2)
    files.append(root/'retrieval_manifest.json')
    archive=root/'diagnostic_results.tar.gz'
    with tarfile.open(archive,'x:gz') as tar:
        for f in files:tar.add(f,arcname=str(f.relative_to(root)),recursive=False)
    if any(sha(root/name)!=h for name,h in manifest['files'].items()):
        raise RuntimeError('source changed while archiving; retrieval not verified')
    return {'archive':str(archive),'sha256':sha(archive),'files':len(files),'bytes':archive.stat().st_size,
            'responses_present':manifest['responses_present']}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    print(json.dumps(export(a.root)))


if __name__=='__main__':main()
