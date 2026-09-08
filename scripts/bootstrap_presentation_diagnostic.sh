#!/usr/bin/env bash
# One fixed diagnostic. Run only after a scoped external guard is armed.
set -euo pipefail
cd /workspace/latenttarget-presentation-20260909
export TOKENIZERS_PARALLELISM=false
export PYTHONDONTWRITEBYTECODE=1
export HF_HOME=/workspace/latenttarget-presentation-20260909/hf-cache
if [[ -d /workspace/latenttarget-extension-20260909/hf-cache ]]; then
  export HF_HOME=/workspace/latenttarget-extension-20260909/hf-cache
fi
if [[ -x /workspace/latenttarget-extension-20260909/runtime/bin/python ]]; then
  PRESENTATION_PYTHON=/workspace/latenttarget-extension-20260909/runtime/bin/python
else
  python3 -m venv runtime
  PRESENTATION_PYTHON=/workspace/latenttarget-presentation-20260909/runtime/bin/python
  "$PRESENTATION_PYTHON" -m pip install --upgrade pip
  "$PRESENTATION_PYTHON" -m pip install --no-cache-dir -r package/requirements-local.txt -r package/requirements-pod.txt
fi
PRESENTATION_NVLIB=$("$PRESENTATION_PYTHON" - <<'PY'
import glob,os,site
print(':'.join(sorted({p for s in site.getsitepackages() for p in glob.glob(os.path.join(s,'nvidia','*','lib'))})))
PY
)
export LD_LIBRARY_PATH="${PRESENTATION_NVLIB}:${LD_LIBRARY_PATH:-}"
"$PRESENTATION_PYTHON" - <<'PY'
import json,os,sys,torch,transformers
from pathlib import Path
e={'python':sys.version,'executable':sys.executable,'torch':torch.__version__,
   'transformers':transformers.__version__,'cuda':torch.version.cuda,
   'gpu_count':torch.cuda.device_count(),'gpu':torch.cuda.get_device_name(0),
   'gpu_memory_bytes':torch.cuda.get_device_properties(0).total_memory,
   'workspace_mount':os.path.ismount('/workspace')}
with Path('hardware_preflight.json').open('x') as f:json.dump(e,f,indent=2)
print(json.dumps(e),flush=True)
assert e['workspace_mount'] and e['gpu_count']==1 and 'A100' in e['gpu']
assert e['gpu_memory_bytes']>=75*1024**3 and torch.cuda.is_bf16_supported()
PY
"$PRESENTATION_PYTHON" package/scripts/run_presentation_diagnostic.py
"$PRESENTATION_PYTHON" package/scripts/run_presentation_diagnostic.py --mode hf --execute --approval approval.json --output responses
