# Diagnostic collection only

This package does not create a pod. No credentials are included. Do not store
outputs inside it. Use Python 3.12 on Linux and one A100 80GB for the real run.
The original project virtual environment is not part of this archive.

Verify without model dependencies:
`python scripts/run_diagnostic_pilot.py`

Mock collection after installing requirements-local.txt:
`python scripts/run_diagnostic_pilot.py --mode mock --output ../mock-results`

On an approved pod, install requirements-local.txt and requirements-pod.txt in
a fresh virtual environment. Do not unpin the torch/torchvision/torchaudio trio.
Place model cache and outputs on the new pod's persistent /workspace volume.
Before loading weights, the operator must verify the live price, storage,
absolute two hour pod deadline, external stop watchdog and result retrieval.
Process timeout alone does not stop GPU billing. Stopped volume storage still
costs money. Download the results before disposing of that exact pod volume.

Real collection requires a separate approval file created by the operator
after the user approves the exact packet and diagnostic budget:
`python scripts/run_diagnostic_pilot.py --mode hf --execute --approval ../approval.json --output ../pilot-results`

The runner requires the pinned model revision, runtime versions, single GPU,
BF16, no offload, no activation capture, at most 12,000 prompt tokens, strict
digit choices, and exactly 60 planned requests. A failed or uncertain request
is recorded and stops collection without retry or random fallback. It never
starts a second study. No confirmatory inference is allowed at three bundles.
