#!/usr/bin/env python3
"""Privacy-sanitize saved Codex judge process metadata in place.

Exact judge inputs and final outputs are untouched. Only duplicated stdout,
environmental stderr, and machine-local temporary paths in ``*.meta.json`` are
replaced by hashes, byte counts, and stable placeholders.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import sys
import tempfile

from src.blind_judge import sanitize_codex_meta


def sanitize_directory(artifact_dir: str) -> int:
    names = sorted(
        name for name in os.listdir(artifact_dir) if name.endswith(".meta.json")
    )
    if not names:
        raise ValueError("no judge metadata artifacts in %s" % artifact_dir)
    changed = 0
    for name in names:
        path = os.path.join(artifact_dir, name)
        with open(path, "r", encoding="utf-8") as fh:
            original = json.load(fh)
        clean = sanitize_codex_meta(original)
        if clean == original:
            continue
        fd, tmp_path = tempfile.mkstemp(
            prefix=".sanitize-", suffix=".json", dir=artifact_dir
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(clean, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
        changed += 1
    return changed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", required=True)
    args = parser.parse_args(argv)
    changed = sanitize_directory(args.artifact_dir)
    print("sanitized %d metadata files in %s" % (changed, args.artifact_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
