from pathlib import Path

import pytest

from scripts.verify_partner_offline import inside


def test_manifest_rejects_paths_outside_root(tmp_path):
    for name in ("../secret", "/etc/passwd", "a/../../secret"):
        with pytest.raises(ValueError):
            inside(tmp_path,name)
    assert inside(tmp_path,"simulations/a.jsonl.gz") == tmp_path/"simulations/a.jsonl.gz"


def test_manifest_rejects_symlink_escape(tmp_path):
    (tmp_path/"escape").symlink_to(Path("/"), target_is_directory=True)
    with pytest.raises(ValueError):
        inside(tmp_path,"escape/etc/passwd")
