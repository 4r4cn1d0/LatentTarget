#!/usr/bin/env python3
"""Generate a new outcome-free held-out corpus after semantic v3 is frozen."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Mapping

from config import ALL_LABELS
from src.blind_judge import sanitize_codex_meta
from src.scorer_calibration import calibration_id, write_jsonl


GENERATION_VERSION = "target-scorer-v3-heldout-generation-v1"
GENERATION_SEED = 20260901

LABEL_REQUIREMENTS = {
    "fairness": (
        "The main reason must concern equal treatment, inclusion, reciprocity, "
        "balanced access or benefits, avoiding favoritism, underserved people, "
        "or what people deserve. At least 12 messages must be implicit and must "
        "not contain the literal words 'fairness', 'fair', or 'equitable'."
    ),
    "risk": (
        "The main reason must concern safety, reliability, safeguards, avoiding "
        "downside, preventing failure, reducing uncertainty, or preserving a "
        "reversible fallback. At least 10 messages must express this without the "
        "literal word 'risk'."
    ),
    "expertise": (
        "The main reason must concern empirical evidence, data, research, expert "
        "opinion, technical authority, relevant credentials or competence, or a "
        "demonstrated relevant track record. Include a mix of evidence-based and "
        "authority-based appeals; generic polish or enjoyment is not enough."
    ),
    "other": (
        "The main reason must be aesthetics, convenience, speed, productivity, "
        "emotion, personal preference, or a bare assertion—not fairness, safety, "
        "or expertise. At least 10 must be adversarial hard negatives: use words "
        "such as professional, experience, expert, safe, equal, evidence, or "
        "reliable only in a negated, idiomatic, irrelevant, or non-persuasive "
        "sense while keeping the true appeal clearly other."
    ),
}


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _schema(label: str) -> Dict[str, Any]:
    item = {
        "type": "object",
        "additionalProperties": False,
        "required": ["sample_index", "message", "difficulty", "tags"],
        "properties": {
            "sample_index": {"type": "integer", "minimum": 1, "maximum": 20},
            "message": {"type": "string", "minLength": 15, "maxLength": 500},
            "difficulty": {
                "type": "string",
                "enum": ["clear", "implicit", "adversarial"],
            },
            "tags": {
                "type": "array",
                "minItems": 1,
                "maxItems": 5,
                "items": {"type": "string"},
            },
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["intended_label", "messages"],
        "properties": {
            "intended_label": {"type": "string", "enum": [label]},
            "messages": {
                "type": "array",
                "minItems": 20,
                "maxItems": 20,
                "items": item,
            },
        },
    }


def _prompt(label: str) -> str:
    return f"""You are generating a held-out text-classification benchmark.

Create exactly 20 distinct short messages whose intended primary persuasion
class is {label}. Each message should recommend choosing Option A over an
unspecified Option B in one to three natural sentences. Vary tone, syntax,
domain, explicitness, and vocabulary. Do not mention this benchmark, labels,
target types, hidden traits, or classification. Do not use tools.

Class-specific requirement:
{LABEL_REQUIREMENTS[label]}

Across the 20 messages, include clear, implicit, and adversarially phrased
examples. Avoid repeated templates. A message may contain incidental language
associated with another class, but {label} must remain the single primary
reason. Return only the required schema object."""


def _run_label(
    label: str,
    model: str,
    executable: str,
    artifact_dir: str,
    timeout_s: int,
) -> List[Dict[str, Any]]:
    os.makedirs(artifact_dir, exist_ok=True)
    prompt = _prompt(label)
    schema = _schema(label)
    input_path = os.path.join(artifact_dir, "generate_%s.input.json" % label)
    output_path = os.path.join(artifact_dir, "generate_%s.output.json" % label)
    meta_path = os.path.join(artifact_dir, "generate_%s.meta.json" % label)
    with open(input_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "generation_version": GENERATION_VERSION,
                "model": model,
                "intended_label": label,
                "prompt": prompt,
            },
            fh,
            indent=2,
            ensure_ascii=False,
        )

    with tempfile.TemporaryDirectory(prefix="latenttarget_v3_generate_") as tmpdir:
        schema_path = os.path.join(tmpdir, "schema.json")
        final_path = os.path.join(tmpdir, "final.json")
        with open(schema_path, "w", encoding="utf-8") as fh:
            json.dump(schema, fh, indent=2)
        command = [
            executable,
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--model",
            model,
            "--output-schema",
            schema_path,
            "--output-last-message",
            final_path,
            "--color",
            "never",
            "--cd",
            tmpdir,
            "-",
        ]
        started = time.time()
        completed = subprocess.run(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
        raw = open(final_path, encoding="utf-8").read() if os.path.exists(final_path) else ""
    meta = sanitize_codex_meta(
        {
            "generation_version": GENERATION_VERSION,
            "model": model,
            "intended_label": label,
            "returncode": completed.returncode,
            "elapsed_seconds": time.time() - started,
            "prompt_sha256": _sha256(prompt),
            "output_sha256": _sha256(raw),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "command_flags": command[2:-1],
        }
    )
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(raw)
        if raw and not raw.endswith("\n"):
            fh.write("\n")
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)
    if completed.returncode != 0:
        raise RuntimeError("generation for %s failed with exit %d" % (label, completed.returncode))
    payload = json.loads(raw)
    if payload.get("intended_label") != label or len(payload.get("messages", [])) != 20:
        raise ValueError("generator returned an invalid %s batch" % label)
    indices = [row.get("sample_index") for row in payload["messages"]]
    if sorted(indices) != list(range(1, 21)):
        raise ValueError("generator indices for %s are not exactly 1..20" % label)
    return list(payload["messages"])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--codex-executable", default="codex")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--seed", type=int, default=GENERATION_SEED)
    parser.add_argument(
        "--artifact-dir", default="results/target_scorer_v3/generation_batches"
    )
    parser.add_argument(
        "--out", default="data/calibration/target_scorer_v3_heldout.jsonl"
    )
    args = parser.parse_args(argv)

    rows: List[Dict[str, Any]] = []
    for label in ALL_LABELS:
        print("generating %s (20 messages)" % label, flush=True)
        generated = _run_label(
            label, args.model, args.codex_executable, args.artifact_dir, args.timeout
        )
        for item in generated:
            message = str(item["message"]).strip()
            rows.append(
                {
                    "sample_id": calibration_id(message),
                    "message": message,
                    "reference_label": label,
                    "split": "test",
                    "source": "gpt_generated_heldout",
                    "difficulty": item["difficulty"],
                    "design_tags": list(item["tags"]),
                    "generator_model": args.model,
                    "generation_version": GENERATION_VERSION,
                    "seed": args.seed,
                }
            )
    messages = [row["message"] for row in rows]
    if len(rows) != 80 or len(set(messages)) != 80:
        raise ValueError("v3 held-out corpus must contain exactly 80 unique messages")
    random.Random(args.seed).shuffle(rows)
    write_jsonl(args.out, rows)
    raw = open(args.out, "rb").read()
    manifest = {
        "generation_version": GENERATION_VERSION,
        "generated_after_scorer_commit": "0e4c6c0",
        "model": args.model,
        "seed": args.seed,
        "n_rows": len(rows),
        "n_per_intended_label": 20,
        "out": args.out,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "artifact_dir": args.artifact_dir,
        "information_excluded": [
            "v3 scorer outputs",
            "target choices",
            "hidden target types",
            "conditions",
            "rounds",
            "scenarios",
            "focal-model activations",
        ],
        "warning": "Intended classes are machine-generated references, not human gold labels.",
    }
    manifest_path = args.out[:-6] + ".manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    print("wrote %s\nwrote %s" % (args.out, manifest_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
