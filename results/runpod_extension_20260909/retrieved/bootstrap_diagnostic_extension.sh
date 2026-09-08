#!/usr/bin/env bash
# Run only inside the fresh diagnostic pod after the external guard is armed.
set -euo pipefail
cd /workspace/latenttarget-extension-20260909
export HF_HOME=/workspace/latenttarget-extension-20260909/hf-cache
export TOKENIZERS_PARALLELISM=false
export PYTHONDONTWRITEBYTECODE=1
python3 -m venv runtime
runtime/bin/python -m pip install --upgrade pip
runtime/bin/python -m pip install --no-cache-dir -r package/requirements-local.txt -r package/requirements-pod.txt
# NVIDIA libraries installed by the wheel must be visible to the loader.
EXTENSION_NVLIB=$(runtime/bin/python - <<'PY'
import glob,os,site
paths=sorted({p for s in site.getsitepackages() for p in glob.glob(os.path.join(s,'nvidia','*','lib'))})
print(':'.join(paths))
PY
)
export LD_LIBRARY_PATH="${EXTENSION_NVLIB}:${LD_LIBRARY_PATH:-}"
runtime/bin/python - <<'PY'
import json,os,sys,torch,transformers
from pathlib import Path
e={'python':sys.version,'torch':torch.__version__,'transformers':transformers.__version__,
   'cuda':torch.version.cuda,'gpu_count':torch.cuda.device_count(),
   'gpu':torch.cuda.get_device_name(0),'gpu_memory_bytes':torch.cuda.get_device_properties(0).total_memory,
   'workspace_mount':os.path.ismount('/workspace')}
with Path('hardware_preflight.json').open('x') as f:json.dump(e,f,indent=2)
print(json.dumps(e),flush=True)
assert e['workspace_mount'], 'persistent workspace mount absent'
assert e['gpu_count']==1 and 'A100' in e['gpu'] and e['gpu_memory_bytes']>=75*1024**3
assert torch.cuda.is_bf16_supported()
PY
runtime/bin/python package/scripts/run_diagnostic_extension.py
runtime/bin/python package/scripts/run_diagnostic_extension.py --mode hf --execute --approval approval.json --output responses
