#!/usr/bin/env bash
# V4 replication (Gemma-4-31B, arm R1) then elicited-belief arm (Qwen3.8-27B, E1),
# sequentially on one A100-80GB pod. Fail-closed: any audit failure stops that arm.
#   bash bootstrap.sh <COMMIT>
set -euo pipefail
COMMIT="${1:?commit sha required}"
export HF_HOME="${HF_HOME:-/workspace/hf-cache}" TOKENIZERS_PARALLELISM=false
[ -d LatentTarget ] || git clone https://github.com/4r4cn1d0/LatentTarget
cd LatentTarget && git fetch --all -q && git checkout -q "$COMMIT" && [ -z "$(git status --porcelain)" ] && echo "checked out $(git rev-parse HEAD)"
python3 -m venv .venv && . .venv/bin/activate && pip -q install --upgrade pip && pip -q install -r requirements.txt -r requirements-pod.txt
pip -q install "torch==2.9.1" "torchvision" "torchaudio==2.9.1" --index-url https://download.pytorch.org/whl/cu128 || pip -q install "torch==2.9.1" "torchvision" "torchaudio==2.9.1"
NVLIB=$(python - <<'PY'
import glob, os, site; print(":".join(sorted(set(os.path.dirname(p) for sp in site.getsitepackages() for p in glob.glob(os.path.join(sp,"nvidia","*","lib"))))))
PY
); export LD_LIBRARY_PATH="${NVLIB}:${LD_LIBRARY_PATH:-}"
python -c "import torch, transformers; print('torch', torch.__version__, 'gpu', torch.cuda.get_device_name(0), 'transformers', transformers.__version__); assert transformers.__version__.startswith('5.')"
python -m pytest -q -p no:warnings tests/test_v8_protocol_gate.py 2>&1 | tail -1
python scripts/run_controlled_open_weight.py --checkpoint-spec docs/v4_paraphrase_qwen38.json --run-id v4p-qwen38 --dry-run | tail -2
echo "=== ARM P1: Qwen3.8-27B paraphrase ($(date -u +%H:%MZ)) ==="
python scripts/run_controlled_open_weight.py --checkpoint-spec docs/v4_paraphrase_qwen38.json --run-id v4p-qwen38 --resume --quiet && echo "=== ARM P1 DONE ($(date -u +%H:%MZ)) ==="
ls -la data/raw/v4r-gemma4.jsonl data/raw/v4e-qwen38.jsonl
echo "=== done. Pull data/raw/v4p-qwen38.*, then STOP THE POD. ==="
