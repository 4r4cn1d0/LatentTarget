"""Small fail-closed filesystem primitives for official experiment runs.

The V6 launch receipts prevent a second nominal run, while these advisory
locks prevent two live processes from consuming the same next paid coordinate.
Lock files intentionally persist after release; the operating-system lock, not
file existence, is the ownership signal, so a process crash releases it.
"""

from __future__ import annotations

import json
import os
import stat
import time
from typing import Any, Mapping, Optional

from .logging_utils import _contained_open_target, _make_contained_directories

try:  # POSIX (the local Mac and RunPod Linux hosts)
    import fcntl as _fcntl
except ImportError:  # pragma: no cover - Windows path
    _fcntl = None

try:  # Windows fallback
    import msvcrt as _msvcrt
except ImportError:  # pragma: no cover - POSIX path
    _msvcrt = None


def fsync_directory_best_effort(path: str) -> None:
    """Sync a directory entry when the platform/filesystem supports it."""
    descriptor: Optional[int] = None
    try:
        descriptor = os.open(path or os.curdir, os.O_RDONLY)
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        if descriptor is not None:
            os.close(descriptor)


def require_regular_nonsymlink(
    path: str,
    *,
    label: str = "artifact",
    allow_missing: bool = False,
) -> None:
    """Reject symlinks, directories, devices, and other non-regular paths."""
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        if allow_missing:
            return
        raise FileNotFoundError("%s is missing: %s" % (label, path)) from None
    if stat.S_ISLNK(metadata.st_mode):
        raise ValueError("%s must not be a symlink: %s" % (label, path))
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("%s must be a regular file: %s" % (label, path))


def require_directory_nonsymlink(
    path: str,
    *,
    label: str = "directory",
    allow_missing: bool = False,
) -> None:
    """Reject symlinked or non-directory canonical output parents."""
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        if allow_missing:
            return
        raise FileNotFoundError("%s is missing: %s" % (label, path)) from None
    if stat.S_ISLNK(metadata.st_mode):
        raise ValueError("%s must not be a symlink: %s" % (label, path))
    if not stat.S_ISDIR(metadata.st_mode):
        raise ValueError("%s must be a directory: %s" % (label, path))


def require_contained_path(path: str, root: str, *, label: str = "artifact") -> str:
    """Return an absolute child path whose resolved location stays in ``root``.

    ``realpath`` resolves every existing symlink component and also resolves a
    missing leaf through its existing parent.  Comparing both lexical and
    resolved locations prevents ``root/link/out.json`` from escaping through a
    symlinked directory while preserving the caller's canonical absolute path.
    """
    absolute_root = os.path.abspath(root)
    absolute_path = os.path.abspath(path)
    try:
        lexical_contained = (
            os.path.commonpath([absolute_root, absolute_path]) == absolute_root
        )
        resolved_root = os.path.realpath(absolute_root)
        resolved_path = os.path.realpath(absolute_path)
        resolved_contained = (
            os.path.commonpath([resolved_root, resolved_path]) == resolved_root
        )
    except ValueError:
        lexical_contained = False
        resolved_contained = False
    if not lexical_contained or not resolved_contained:
        raise ValueError("%s leaves its canonical root: %s" % (label, path))
    return absolute_path


class ExclusiveFileLock:
    """Mandatory non-blocking lock with POSIX and Windows implementations."""

    def __init__(
        self,
        path: str,
        *,
        label: str = "official run",
        metadata: Optional[Mapping[str, Any]] = None,
        root: Optional[str] = None,
    ) -> None:
        self.path = os.path.abspath(path)
        self.label = str(label)
        self.metadata = dict(metadata or {})
        self.root = os.path.abspath(root) if root is not None else None
        self._descriptor: Optional[int] = None
        self._backend: Optional[str] = None

    def acquire(self) -> "ExclusiveFileLock":
        if self._descriptor is not None:
            raise RuntimeError("%s lock is already held" % self.label)
        if _fcntl is None and _msvcrt is None:
            raise RuntimeError(
                "%s requires an operating-system exclusive-lock backend"
                % self.label
            )
        parent = os.path.dirname(self.path) or os.curdir
        parent_descriptor: Optional[int] = None
        leaf: Optional[str] = None
        if self.root is None:
            os.makedirs(parent, exist_ok=True)
            require_directory_nonsymlink(parent, label=self.label + " lock parent")
            require_regular_nonsymlink(
                self.path, label=self.label + " lock file", allow_missing=True
            )
        else:
            _make_contained_directories(parent, self.root, self.label + " lock")
            parent_descriptor, leaf = _contained_open_target(
                self.path, self.root, self.label + " lock"
            )
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        if hasattr(os, "O_NONBLOCK"):
            flags |= os.O_NONBLOCK
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        try:
            descriptor = (
                os.open(self.path, flags, 0o600)
                if parent_descriptor is None
                else os.open(leaf, flags, 0o600, dir_fd=parent_descriptor)
            )
        except BaseException:
            if parent_descriptor is not None:
                os.close(parent_descriptor)
            raise
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError("%s lock is not a regular file" % self.label)
            if _fcntl is not None:
                try:
                    _fcntl.flock(descriptor, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
                except BlockingIOError as exc:
                    raise RuntimeError(
                        "another process holds the %s lock" % self.label
                    ) from exc
                self._backend = "fcntl"
            else:  # pragma: no cover - Windows path
                os.lseek(descriptor, 0, os.SEEK_SET)
                if os.fstat(descriptor).st_size == 0:
                    os.write(descriptor, b"\0")
                    os.fsync(descriptor)
                os.lseek(descriptor, 0, os.SEEK_SET)
                try:
                    _msvcrt.locking(descriptor, _msvcrt.LK_NBLCK, 1)
                except OSError as exc:
                    raise RuntimeError(
                        "another process holds the %s lock" % self.label
                    ) from exc
                self._backend = "msvcrt"

            owner = {
                "lock_version": "latenttarget-exclusive-lock-v1",
                "label": self.label,
                "pid": os.getpid(),
                "acquired_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "metadata": self.metadata,
            }
            encoded = (json.dumps(owner, sort_keys=True) + "\n").encode("utf-8")
            os.lseek(descriptor, 0, os.SEEK_SET)
            os.ftruncate(descriptor, 0)
            offset = 0
            while offset < len(encoded):
                offset += os.write(descriptor, encoded[offset:])
            os.fsync(descriptor)
            if parent_descriptor is None:
                fsync_directory_best_effort(parent)
            else:
                try:
                    os.fsync(parent_descriptor)
                except OSError:
                    pass
            self._descriptor = descriptor
            return self
        except BaseException:
            os.close(descriptor)
            raise
        finally:
            if parent_descriptor is not None:
                os.close(parent_descriptor)

    def release(self) -> None:
        descriptor = self._descriptor
        if descriptor is None:
            return
        try:
            if self._backend == "fcntl":
                _fcntl.flock(descriptor, _fcntl.LOCK_UN)
            elif self._backend == "msvcrt":  # pragma: no cover - Windows path
                os.lseek(descriptor, 0, os.SEEK_SET)
                _msvcrt.locking(descriptor, _msvcrt.LK_UNLCK, 1)
        finally:
            os.close(descriptor)
            self._descriptor = None
            self._backend = None

    def __enter__(self) -> "ExclusiveFileLock":
        return self.acquire()

    def __exit__(self, *_exc: Any) -> None:
        self.release()
