from __future__ import annotations

import os

import pytest

import src.file_lock as file_lock
from src.file_lock import (
    ExclusiveFileLock,
    require_contained_path,
    require_directory_nonsymlink,
    require_regular_nonsymlink,
)


def test_exclusive_lock_rejects_concurrent_holder(tmp_path):
    path = tmp_path / "official.lock"
    first = ExclusiveFileLock(str(path), label="test run")
    first.acquire()
    try:
        with pytest.raises(RuntimeError, match="another process"):
            ExclusiveFileLock(str(path), label="test run").acquire()
    finally:
        first.release()
    with ExclusiveFileLock(str(path), label="test run"):
        assert path.is_file()


def test_exclusive_lock_fails_if_no_backend(monkeypatch, tmp_path):
    monkeypatch.setattr(file_lock, "_fcntl", None)
    monkeypatch.setattr(file_lock, "_msvcrt", None)
    with pytest.raises(RuntimeError, match="requires.*backend"):
        ExclusiveFileLock(str(tmp_path / "lock")).acquire()


def test_path_guards_reject_symlinks_and_escape(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    linked_file = root / "linked.txt"
    linked_file.symlink_to(outside)
    linked_dir = root / "linked-dir"
    linked_dir.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        require_regular_nonsymlink(str(linked_file))
    with pytest.raises(ValueError, match="symlink"):
        require_directory_nonsymlink(str(linked_dir))
    with pytest.raises(ValueError, match="leaves"):
        require_contained_path(str(tmp_path / "escape"), str(root))
    with pytest.raises(ValueError, match="leaves"):
        require_contained_path(str(linked_dir / "escaped.json"), str(root))


def test_lock_rejects_symlink_file(tmp_path):
    target = tmp_path / "target"
    target.write_text("", encoding="utf-8")
    link = tmp_path / "lock"
    os.symlink(target, link)
    with pytest.raises(ValueError, match="symlink"):
        ExclusiveFileLock(str(link)).acquire()
