#!/usr/bin/env bash
# One-paste bootstrap for the V8 Gemma-4-31B prior measurement on a fresh RunPod
# A100 80GB pod. Fail-closed: any step failing stops the script before money is
# spent on generation. Usage on the pod:
#
#   bash <(curl -fsSL https://raw.githubusercontent.com/4r4cn1d0/LatentTarget/<COMMIT>/scripts/pod_bootstrap_v8.sh) <COMMIT>
#   -- or, if the repo was rsynced instead of pushed --
#   cd ~/LatentTarget && bash scripts/pod_bootstrap_v8.sh --local
#
set -euo pipefail
COMMIT="${1:-}"
MODEL_KEY="${MODEL_KEY:-gemma4_31b}"
RUN_ID="${RUN_ID:-v8-gemma4-prior}"
export HF_HOME="${HF_HOME:-/workspace/hf-cache}"      # container disk, NOT the 100 GB V5 volume
export TOKENIZERS_PARALLELISM=false

if [ "$COMMIT" != "--local" ]; then
  [ -n "$COMMIT" ] || { echo "usage: pod_bootstrap_v8.sh <commit-sha> | --local"; exit 2; }
  [ -d LatentTarget ] || git clone https://github.com/4r4cn1d0/LatentTarget
  cd LatentTarget && git fetch --all -q && git checkout -q "$COMMIT"
  [ -z "$(git status --porcelain)" ] || { echo "dirty tree; refusing"; exit 3; }
  echo "checked out $(git rev-parse HEAD)"
fi

python3 -m venv .venv && . .venv/bin/activate
pip -q install --upgrade pip
pip -q install -r requirements.txt -r requirements-pod.txt
# V4 pitfall 1: template torch 2.8 vs pinned 2.9.1 -- pin the trio together.
pip -q install "torch==2.9.1" "torchvision" "torchaudio==2.9.1" --index-url https://download.pytorch.org/whl/cu128 || \
pip -q install "torch==2.9.1" "torchvision" "torchaudio==2.9.1"
# V4 pitfall 2: libcusparseLt.so.0 not on the loader path.
NVLIB=$(python - <<'PY'
import glob, os, site
paths = sorted(set(os.path.dirname(p) for sp in site.getsitepackages() for p in glob.glob(os.path.join(sp, "nvidia", "*", "lib"))))
print(":".join(paths))
PY
)
export LD_LIBRARY_PATH="${NVLIB}:${LD_LIBRARY_PATH:-}"
python - <<'PY'
import torch, transformers
print("torch", torch.__version__, "cuda", torch.version.cuda, "gpu", torch.cuda.get_device_name(0))
print("transformers", transformers.__version__)
assert transformers.__version__.startswith("5."), "Gemma4 needs transformers 5.x"
PY

# Protocol + gate tests first; cheap.
python -m pytest -q -p no:warnings tests/test_v8_protocol_gate.py tests/test_controlled_v8_power.py tests/test_register_v8_prior.py

# The exact measurement command, audited with no model loaded.
python scripts/run_v8_prior_measurement.py --model-key "$MODEL_KEY" --run-id "$RUN_ID" --dry-run

# Loader + template + digits smoke test BEFORE the 576-choice run.
python - <<PY
import json
from src.hf_provider import HuggingFaceProvider
spec = json.load(open("docs/v8_protocol.json")); m = spec["models"]["$MODEL_KEY"]; g = spec["generation"]
p = HuggingFaceProvider(model=m["id"], revision=m["revision"], temperature=g["temperature"], max_tokens=g["max_tokens"],
                        dtype=g["dtype"], capture=False, seed=spec["prior_measurement_schedule"]["seed"],
                        enable_thinking=g["enable_thinking"], top_p=g["top_p"], top_k=g["top_k"],
                        constrained_choices=tuple(g["constrained_choices"]))
p._ensure_loaded(); d = p.describe(); print({k: d[k] for k in ("model", "revision", "architecture", "loaded_with")})
tok = p._tok
for digit in g["constrained_choices"]:
    assert len(tok.encode(digit, add_special_tokens=False)) == 1, digit
print("digits single-token: OK")
PY

echo "=== all gates passed; starting the measurement (576 constrained choices) ==="
python scripts/run_v8_prior_measurement.py --model-key "$MODEL_KEY" --run-id "$RUN_ID"
echo "=== done. Pull data/calibration/${RUN_ID}.jsonl and its .manifest.json, then STOP THE POD. ==="
