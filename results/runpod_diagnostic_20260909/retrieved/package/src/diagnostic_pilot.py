"""Bounded, resumable choice collection. Does not provision or stop a GPU pod.

Only exact system/user strings cross the provider boundary. Analyst metadata is
kept separately. A durable claim precedes each call; ambiguous calls never retry.
"""
from collections import Counter
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import signal
import time

MODEL = "Qwen/Qwen3.8-27B"
REVISION = "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
BRANCHES = ("BIND", "NEAR", "TRANSFER", "NO_HISTORY", "RANDOM_RESPONSE")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write_new(path, value):
    """A truncated write is deliberately not treated as a successful response."""
    with Path(path).open("x") as f:
        json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.flush()
        os.fsync(f.fileno())
    fd = os.open(Path(path).parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def verify_package(root):
    root = Path(root).resolve()
    manifest = read(root / "package_manifest.json")
    expected = manifest["files"]
    actual = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}
    if actual != set(expected) | {"package_manifest.json"}:
        raise ValueError("package has missing or unexpected files; put outputs outside the package")
    for name, sha in expected.items():
        p = root / name
        if p.is_symlink() or not p.resolve().is_relative_to(root) or file_sha(p) != sha:
            raise ValueError("package hash or path mismatch")
    return manifest


def validate_packet(packet):
    cfg, rows = packet["config"], packet["requests"]
    if cfg["model"] != MODEL or cfg["revision"] != REVISION:
        raise ValueError("unexpected focal checkpoint")
    g = cfg["generation"]
    if g != dict(temperature=.7, max_tokens=16, device="cuda:0", dtype="bfloat16", capture=False,
                 seed=202609089, enable_thinking=False, top_p=.8, top_k=20, constrained_choices=["1", "2", "3"]):
        raise ValueError("generation settings changed")
    if cfg["n_bundles"] != 3 or cfg["max_requests"] != 60 or len(rows) != 60:
        raise ValueError("diagnostic request budget is exactly 60")
    if cfg["max_input_tokens"] != 12000 or cfg["max_run_seconds"] != 3600:
        raise ValueError("runtime limits changed")
    ids = set()
    groups = Counter()
    for index, r in enumerate(rows):
        if set(r) != {"request_id", "bundle_id", "spec", "prompt", "prompt_sha256", "execution_index", "seed"}:
            raise ValueError("request projection fields changed")
        s = r["spec"]
        if (set(s) != {"bank", "branch", "cell", "rebound", "recipient"} or s["branch"] not in BRANCHES
                or type(s["cell"]) is not int or s["cell"] not in range(4)):
            raise ValueError("request cell invalid")
        cell = s["cell"]
        bank = ("familiar" if cell < 2 else "composite") if s["branch"] == "NO_HISTORY" else {"BIND":"familiar", "NEAR":"near", "TRANSFER":"composite", "RANDOM_RESPONSE":"familiar"}[s["branch"]]
        if s != dict(branch=s["branch"], cell=cell, bank=bank, recipient=cell % 2,
                     rebound=False if s["branch"] == "NO_HISTORY" else cell >= 2):
            raise ValueError("declared cell does not match request specification")
        if r["request_id"] != f"{r['bundle_id']}/{s['branch']}/{cell}" or r["request_id"] in ids:
            raise ValueError("unknown or duplicate request ID")
        if r["execution_index"] != index or r["seed"] != int(digest([202609089, r["request_id"]])[:8], 16):
            raise ValueError("execution order or seed changed")
        if set(r["prompt"]) != {"system", "user"} or any(not isinstance(v, str) or not v for v in r["prompt"].values()):
            raise ValueError("provider prompt must contain only system and user strings")
        if digest(r["prompt"]) != r["prompt_sha256"]:
            raise ValueError("prompt hash mismatch")
        ids.add(r["request_id"])
        groups[(r["bundle_id"], s["branch"])] += 1
    if len({r["bundle_id"] for r in rows}) != 3 or len(groups) != 15 or set(groups.values()) != {4}:
        raise ValueError("incomplete diagnostic bundle")
    return digest(packet)


def check_approval(approval, packet_sha):
    required = {"packet_sha256", "approved", "pod_id", "maximum_requests", "maximum_total_usd", "hourly_quote_usd", "pod_deadline_utc", "stop_watchdog_verified", "results_on_persistent_volume"}
    if set(approval) != required or approval["approved"] is not True or approval["packet_sha256"] != packet_sha:
        raise ValueError("explicit execution approval does not match packet")
    from datetime import datetime, timezone
    deadline = datetime.fromisoformat(approval["pod_deadline_utc"])
    if deadline.tzinfo is None or not 0 < (deadline - datetime.now(timezone.utc)).total_seconds() <= 7200:
        raise ValueError("pod deadline missing, expired or too distant")
    for field, limit in (("maximum_total_usd", 5), ("hourly_quote_usd", 2)):
        value = approval[field]
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= limit:
            raise ValueError("approved price exceeds diagnostic limit")
    if (approval["maximum_requests"] != 60 or not re.fullmatch(r"[a-zA-Z0-9_-]+", approval["pod_id"])
            or approval["stop_watchdog_verified"] is not True or approval["results_on_persistent_volume"] is not True):
        raise ValueError("deployment safeguards are not attested")


@contextmanager
def deadline(seconds):
    def expired(_signum, _frame):
        raise TimeoutError("diagnostic process time limit reached; this does not stop pod billing")
    old = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


class MockChoiceProvider:
    """Deterministic infrastructure fixture, not evidence of model learning."""
    def set_next_seed(self, seed):
        self.seed = seed

    def generate(self, prompt):
        assert not prompt.context
        return str(1 + int(digest([self.seed, prompt.system, prompt.user])[:8], 16) % 3)


def real_provider(config, evidence_path):
    import torch
    from src.hf_provider import HuggingFaceProvider
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1 or not torch.cuda.is_bf16_supported():
        raise RuntimeError("one BF16 capable CUDA GPU is required")
    gpu = torch.cuda.get_device_properties(0)
    if "A100" not in gpu.name or gpu.total_memory < 75 * 1024**3:
        raise RuntimeError("the approved diagnostic requires one A100 80GB")
    packages = {k: importlib.metadata.version(k) for k in ("torch", "torchvision", "torchaudio", "transformers", "accelerate", "sentencepiece", "numpy")}
    pinned = {"torch":"2.9.1", "torchvision":"0.24.1", "torchaudio":"2.9.1", "transformers":"5.16.1", "accelerate":"1.14.0"}
    if any(packages[k].split("+")[0] != v for k, v in pinned.items()):
        raise RuntimeError("pod dependency versions differ from the approved runtime")
    provider = HuggingFaceProvider(config["model"], revision=config["revision"], **config["generation"])
    provider._ensure_loaded()
    device_map = getattr(provider._model, "hf_device_map", {})
    if provider.capture or any(str(v) in ("cpu", "disk", "meta") for v in device_map.values()):
        raise RuntimeError("activation capture or CPU/disk offload is not allowed")
    write_new(evidence_path, {"packages":packages, "gpu":gpu.name, "memory_bytes":gpu.total_memory,
                            "device_map":{k:str(v) for k,v in device_map.items()}, "provider":provider.describe()})
    return provider


def collect(packet, output, provider_factory=None, mode="mock", approval=None, stop_after=None):
    """Resume only authenticated completed rows. Calls with uncertain status halt.

    stop_after is an engineering test hook used only in mock mode. Real mode
    cannot inject another provider or change the full 60 request schedule.
    """
    packet_sha = validate_packet(packet)
    if mode not in ("mock", "hf"):
        raise ValueError("unknown execution mode")
    if mode == "hf":
        if provider_factory is not None or stop_after is not None:
            raise ValueError("real mode does not permit provider or schedule overrides")
        check_approval(approval or {}, packet_sha)
    out = Path(output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    identity = {"packet_sha256":packet_sha, "mode":mode, "model":packet["config"]["model"] if mode == "hf" else "deterministic_mock",
                "approval_sha256":digest(approval) if approval else None}
    from src.focal_agent import FocalPrompt
    with (out / "run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        run_file = out / "run.json"
        if run_file.exists():
            if read(run_file) != identity:
                raise ValueError("output directory belongs to a different packet, approval or provider")
        else:
            if set(p.name for p in out.iterdir()) != {"run.lock"}:
                raise ValueError("nonempty output directory lacks run identity")
            write_new(run_file, identity)
        planned = {f"{i:03d}.{suffix}.json" for i in range(60) for suffix in ("claim", "response")}
        if any(p.name not in planned | {"run.lock", "run.json", "complete.json"} and not re.fullmatch(r"runtime_[0-9]+\.json", p.name) for p in out.iterdir()):
            raise ValueError("unknown files in collection directory")
        completed, pending = [], []
        for r in packet["requests"]:
            index = r["execution_index"]
            claim_path, response_path = (out / f"{index:03d}.{s}.json" for s in ("claim", "response"))
            claim = dict(identity, request_id=r["request_id"], prompt_sha256=r["prompt_sha256"], seed=r["seed"])
            if response_path.exists() and not claim_path.exists():
                raise ValueError("unclaimed response")
            if claim_path.exists():
                if read(claim_path) != claim:
                    raise ValueError("request claim mismatch")
                if not response_path.exists():
                    raise RuntimeError("uncertain prior call; automatic retry refused")
                response = read(response_path)
                body = {k:v for k,v in response.items() if k != "record_sha256"}
                if response.get("record_sha256") != digest(body) or any(response.get(k) != v for k,v in claim.items()):
                    raise ValueError("response identity or hash mismatch")
                if response.get("status") != "VALID" or response.get("raw_response") not in ("1", "2", "3"):
                    raise RuntimeError("prior response failed; no replacement response is permitted")
                completed.append(response)
            else:
                pending.append((r, claim, claim_path, response_path))
        if completed and pending and max(r["execution_index"] for r in completed) >= min(r["execution_index"] for r, *_ in pending):
            raise ValueError("completed requests are not an execution prefix")
        complete = {**identity, "status":"COMPLETE", "responses":60, "scientific_result":False,
                    "response_hashes":[r["record_sha256"] for r in completed]}
        if not pending:
            if (out / "complete.json").exists() and read(out / "complete.json") != complete:
                raise ValueError("completion manifest changed")
            if not (out / "complete.json").exists():
                write_new(out / "complete.json", complete)
            return complete
        if (out / "complete.json").exists():
            raise ValueError("completion exists but planned responses are missing")
        with deadline(packet["config"]["max_run_seconds"]):
            provider = (provider_factory or MockChoiceProvider)() if mode == "mock" else real_provider(packet["config"], out / f"runtime_{time.time_ns()}.json")
            calls = 0
            for r, claim, claim_path, response_path in pending:
                if mode == "hf":
                    check_approval(approval, packet_sha)
                prompt = FocalPrompt(system=r["prompt"]["system"], user=r["prompt"]["user"])
                token_count = None
                if mode == "hf":
                    if provider.capture:
                        raise RuntimeError("activation capture must remain disabled")
                    inputs = provider._format_inputs(prompt.system, prompt.user)
                    token_count = int(inputs["input_ids"].shape[-1])
                    del inputs
                    if token_count > packet["config"]["max_input_tokens"]:
                        raise RuntimeError("input token limit exceeded; no truncation allowed")
                provider.set_next_seed(r["seed"])
                write_new(claim_path, claim)
                started = time.monotonic()
                failure_type, raw = None, None
                try:
                    raw = provider.generate(prompt)
                except Exception as exc:
                    failure_type = type(exc).__name__
                status = "VALID" if failure_type is None and type(raw) is str and raw in ("1", "2", "3") else "INVALID_OR_FAILED"
                record = dict(claim, execution_index=r["execution_index"], status=status,
                              raw_response=raw if type(raw) is str else None, failure_type=failure_type,
                              input_tokens=token_count, seconds=time.monotonic()-started)
                record["record_sha256"] = digest(record)
                write_new(response_path, record)
                if status != "VALID":
                    raise RuntimeError("response failed strict digit validation; recorded, no fallback or retry")
                completed.append(record)
                calls += 1
                print(json.dumps({"completed":len(completed), "planned":60, "mode":mode}), flush=True)
                if stop_after is not None and calls >= stop_after:
                    return {**identity, "status":"MOCK_PAUSED", "responses":len(completed)}
        complete["response_hashes"] = [r["record_sha256"] for r in completed]
        write_new(out / "complete.json", complete)
        return complete
