"""JSONL logging for experiment records, plus run manifests.

One record per (episode, round).  Nothing is aggregated or filtered at write
time: every message, every prompt and every probability is stored so that the
analysis can be re-run, audited, and re-classified without re-querying any
model.  There is no code path anywhere in this project that drops or selects
episodes -- that is a deliberate guard against cherry-picking.
"""

from __future__ import annotations

import json
import math
import os
import platform
import secrets
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional

#: Fields every record must carry.  Checked by ``validate_record`` and by
#: ``tests/test_experiment.py``.
REQUIRED_FIELDS = (
    "experiment_id",
    "run_id",
    "condition",
    "episode_id",
    "episode_index",
    "round",
    "n_rounds",
    "hidden_target_type",          # type ACTIVE this round
    "initial_target_type",
    "final_target_type",
    "swap_condition",              # bool: does this episode ever swap?
    "swap_round",                  # int or None
    "swap_has_occurred",           # bool: has the swap already happened by now?
    "rounds_since_swap",           # int or None
    "target_mode",                 # "typed" | "random"
    "history_mode",
    "scenario_id",
    "scenario",
    "focal_system_prompt",
    "focal_user_prompt",
    "focal_message_raw",
    "focal_message",
    "visible_history",
    "history_source_episode_id",
    "strategy_scores",
    "primary_strategy",
    "strategy_confidence",
    "classifier_name",
    "target_scores",
    "target_p_a",
    "target_p_a_noiseless",
    "target_logit",
    "target_choice",
    "episode_seed",
    "round_seed",
    "master_seed",
    "model_name",
    "provider",
    "timestamp",
)


def validate_record(record: Dict[str, Any]) -> None:
    missing = [f for f in REQUIRED_FIELDS if f not in record]
    if missing:
        raise ValueError("log record is missing required fields: %s" % ", ".join(missing))


class JsonlWriter:
    """Append-only JSONL writer that flushes after every record."""

    def __init__(
        self,
        path: str,
        validate: bool = True,
        validator: Optional[Callable[[Dict[str, Any]], None]] = None,
        root: Optional[str] = None,
    ) -> None:
        self.path = path
        self.validate = validate
        self.validator = validator or validate_record
        parent = os.path.dirname(path)
        if parent:
            if root is None:
                os.makedirs(parent, exist_ok=True)
            else:
                _make_contained_directories(parent, root, "JSONL log")
        descriptor = _open_regular_descriptor(
            path,
            os.O_WRONLY | os.O_APPEND | os.O_CREAT,
            mode=0o644,
            root=root,
            label="JSONL log",
        )
        try:
            # Keep writing through the descriptor that was opened with
            # O_NOFOLLOW and verified with fstat.  A later path replacement
            # therefore cannot redirect paid-call records to another file.
            self._fh = os.fdopen(descriptor, "a", encoding="utf-8")
        except BaseException:
            os.close(descriptor)
            raise
        self.n_written = 0

    def write(self, record: Dict[str, Any]) -> None:
        if self.validate:
            self.validator(record)
        self._fh.write(
            json.dumps(
                record,
                ensure_ascii=False,
                allow_nan=False,
                default=_json_default,
            )
            + "\n"
        )
        self._fh.flush()
        # Each row can represent a paid model call.  Flush the kernel page
        # cache as well as Python's buffer so an interrupted run can audit and
        # resume the exact durable prefix without repeating that call.
        os.fsync(self._fh.fileno())
        self.n_written += 1

    def close(self) -> None:
        try:
            self._fh.close()
        except Exception:  # pragma: no cover
            pass

    def __enter__(self) -> "JsonlWriter":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


def _json_default(obj: Any) -> Any:
    if hasattr(obj, "as_dict"):
        return obj.as_dict()
    if hasattr(obj, "item"):  # numpy scalars
        try:
            return obj.item()
        except Exception:  # pragma: no cover
            pass
    raise TypeError(
        "Object of type %s is not JSON serializable" % type(obj).__name__
    )


def _make_contained_directories(path: str, root: str, label: str) -> None:
    """Create child directories with openat/mkdirat and no symlink traversal."""
    absolute_root = os.path.abspath(root)
    absolute_path = os.path.abspath(path)
    try:
        contained = (
            os.path.commonpath([absolute_root, absolute_path]) == absolute_root
        )
    except ValueError:
        contained = False
    if not contained:
        raise ValueError("%s leaves its canonical root: %s" % (label, path))
    relative = os.path.relpath(absolute_path, absolute_root)
    parts = [] if relative == os.curdir else relative.split(os.sep)

    directory_flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        directory_flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        directory_flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        directory_flags |= os.O_CLOEXEC
    descriptor: Optional[int] = None
    try:
        descriptor = os.open(absolute_root, directory_flags)
        for component in parts:
            try:
                next_descriptor = os.open(
                    component, directory_flags, dir_fd=descriptor
                )
            except FileNotFoundError:
                os.mkdir(component, dir_fd=descriptor)
                next_descriptor = os.open(
                    component, directory_flags, dir_fd=descriptor
                )
            except OSError as exc:
                raise ValueError(
                    "%s must not traverse symlinked directory components: %s"
                    % (label, path)
                ) from exc
            os.close(descriptor)
            descriptor = next_descriptor
    finally:
        if descriptor is not None:
            os.close(descriptor)


def ensure_contained_directory(
    path: str, root: str, *, label: str = "artifact directory"
) -> None:
    """Create/verify a directory below ``root`` without symlink traversal."""
    _make_contained_directories(path, root, label)


def _contained_open_target(path: str, root: str, label: str) -> tuple[int, str]:
    """Open the containing directory without traversing symlink components."""
    absolute_root = os.path.abspath(root)
    absolute_path = os.path.abspath(path)
    try:
        if os.path.commonpath([absolute_root, absolute_path]) != absolute_root:
            raise ValueError("%s leaves its canonical root: %s" % (label, path))
    except ValueError:
        raise ValueError(
            "%s leaves its canonical root: %s" % (label, path)
        ) from None

    relative = os.path.relpath(absolute_path, absolute_root)
    parts = [] if relative == os.curdir else relative.split(os.sep)
    if not parts or any(part in {"", os.curdir, os.pardir} for part in parts):
        raise ValueError(
            "%s is not a file below its canonical root: %s" % (label, path)
        )

    directory_flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        directory_flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        directory_flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        directory_flags |= os.O_CLOEXEC

    descriptor: Optional[int] = None
    try:
        descriptor = os.open(absolute_root, directory_flags)
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise ValueError("%s root is not a directory: %s" % (label, root))
        for component in parts[:-1]:
            try:
                next_descriptor = os.open(
                    component, directory_flags, dir_fd=descriptor
                )
            except FileNotFoundError:
                raise
            except OSError as exc:
                raise ValueError(
                    "%s must not traverse symlinks or special files: %s"
                    % (label, path)
                ) from exc
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor, parts[-1]
    except BaseException:
        if descriptor is not None:
            os.close(descriptor)
        raise


def _open_regular_descriptor(
    path: str,
    flags: int,
    *,
    mode: int = 0o644,
    root: Optional[str] = None,
    label: str = "artifact",
) -> int:
    """Open and return one no-follow descriptor proven to be a regular file."""
    safe_flags = flags
    if hasattr(os, "O_NOFOLLOW"):
        safe_flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NONBLOCK"):
        # Prevent an attacker-controlled FIFO from blocking before fstat can
        # reject it.  O_NONBLOCK has no effect on ordinary disk files.
        safe_flags |= os.O_NONBLOCK
    if hasattr(os, "O_CLOEXEC"):
        safe_flags |= os.O_CLOEXEC

    parent_descriptor: Optional[int] = None
    try:
        if root is None:
            if not hasattr(os, "O_NOFOLLOW"):
                try:
                    metadata = os.lstat(path)
                except FileNotFoundError:
                    metadata = None
                if metadata is not None and stat.S_ISLNK(metadata.st_mode):
                    raise ValueError("%s must not be a symlink: %s" % (label, path))
            descriptor = os.open(path, safe_flags, mode)
        else:
            parent_descriptor, leaf = _contained_open_target(path, root, label)
            descriptor = os.open(
                leaf, safe_flags, mode, dir_fd=parent_descriptor
            )
    except FileNotFoundError:
        raise
    except ValueError:
        raise
    except OSError as exc:
        raise ValueError(
            "%s must be a regular file and must not be a symlink: %s"
            % (label, path)
        ) from exc
    finally:
        if parent_descriptor is not None:
            os.close(parent_descriptor)

    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("%s must be a regular file: %s" % (label, path))
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def open_regular_read_descriptor(
    path: str,
    *,
    root: Optional[str] = None,
    label: str = "artifact",
) -> int:
    """Return an O_NOFOLLOW read descriptor for a contained regular file."""
    return _open_regular_descriptor(
        path, os.O_RDONLY, root=root, label=label
    )


def _reject_nonfinite_json(value: str) -> None:
    raise ValueError("non-finite JSON constant is forbidden: %s" % value)


def _strict_json_object(pairs: List[tuple[str, Any]]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError("duplicate JSON object key is forbidden: %s" % key)
        payload[key] = value
    return payload


def _strict_json_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("non-finite JSON number is forbidden: %s" % value)
    return parsed


def strict_json_load(handle: Any) -> Any:
    """Load strict JSON, rejecting duplicate keys and non-finite constants."""
    return json.load(
        handle,
        object_pairs_hook=_strict_json_object,
        parse_constant=_reject_nonfinite_json,
        parse_float=_strict_json_float,
    )


def strict_json_loads(document: Any) -> Any:
    """Parse strict JSON, rejecting duplicate keys and non-finite constants."""
    return json.loads(
        document,
        object_pairs_hook=_strict_json_object,
        parse_constant=_reject_nonfinite_json,
        parse_float=_strict_json_float,
    )


def read_jsonl(
    path: str, *, root: Optional[str] = None
) -> Iterator[Dict[str, Any]]:
    descriptor = open_regular_read_descriptor(
        path, root=root, label="JSONL input"
    )
    with os.fdopen(descriptor, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield strict_json_loads(line)


def load_records(paths: Iterable[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in paths:
        out.extend(read_jsonl(p))
    return out


def _git_commit() -> Optional[str]:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
    except Exception:
        return None


def _fsync_directory(path: str) -> None:
    """Best-effort directory sync after an atomic rename.

    Some filesystems do not support syncing directory descriptors.  The file
    itself is always synced before rename; this extra step makes the directory
    entry durable on filesystems that expose the operation.
    """
    descriptor: Optional[int] = None
    try:
        descriptor = os.open(path or ".", os.O_RDONLY)
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _fsync_directory_descriptor(descriptor: int) -> None:
    """Best-effort sync of an already verified directory descriptor."""
    try:
        os.fsync(descriptor)
    except OSError:
        pass


def _reject_symlink_destination_at(
    parent_descriptor: int, leaf: str, path: str
) -> None:
    """Reject a destination symlink relative to a retained parent descriptor."""
    try:
        metadata = os.stat(
            leaf, dir_fd=parent_descriptor, follow_symlinks=False
        )
    except FileNotFoundError:
        return
    if stat.S_ISLNK(metadata.st_mode):
        raise ValueError("artifact destination must not be a symlink: %s" % path)


def _create_regular_temporary_at(
    parent_descriptor: int,
    target_leaf: str,
    *,
    suffix: str,
) -> tuple[int, str]:
    """Create an exclusive O_NOFOLLOW regular temp in an opened directory."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    for _ in range(128):
        temporary_leaf = ".%s.%s%s" % (
            target_leaf,
            secrets.token_hex(8),
            suffix,
        )
        try:
            descriptor = os.open(
                temporary_leaf,
                flags,
                0o600,
                dir_fd=parent_descriptor,
            )
        except FileExistsError:
            continue
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ValueError("atomic-write temporary is not a regular file")
            return descriptor, temporary_leaf
        except BaseException:
            os.close(descriptor)
            try:
                os.unlink(temporary_leaf, dir_fd=parent_descriptor)
            except FileNotFoundError:
                pass
            raise
    raise FileExistsError("could not allocate a unique atomic-write temporary")


def _read_regular_bytes_at(
    parent_descriptor: int,
    leaf: str,
    *,
    path: str,
    label: str,
) -> bytes:
    """Read a regular leaf through a retained parent directory descriptor."""
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    try:
        descriptor = os.open(leaf, flags, dir_fd=parent_descriptor)
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise ValueError(
            "%s must be a regular file and must not be a symlink: %s"
            % (label, path)
        ) from exc
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError("%s must be a regular file: %s" % (label, path))
        chunks = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _reject_symlink_destination(path: str) -> None:
    """Reject a destination symlink, including a broken one."""
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return
    if stat.S_ISLNK(metadata.st_mode):
        raise ValueError("artifact destination must not be a symlink: %s" % path)


def _read_regular_bytes(
    path: str,
    *,
    root: Optional[str] = None,
    label: str = "artifact",
) -> bytes:
    """Read a regular file without following a final-component symlink."""
    descriptor = open_regular_read_descriptor(path, root=root, label=label)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("artifact is not a regular file: %s" % path)
        chunks = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def read_regular_bytes(
    path: str,
    *,
    root: Optional[str] = None,
    label: str = "artifact",
) -> bytes:
    """Read one regular file through a root-anchored descriptor chain."""
    return _read_regular_bytes(path, root=root, label=label)


def atomic_write_bytes(
    path: str,
    data: bytes,
    *,
    mode: int = 0o644,
    root: Optional[str] = None,
) -> None:
    """Durably replace ``path`` with one complete byte sequence."""
    if not isinstance(data, bytes):
        raise TypeError("atomic_write_bytes data must be bytes")
    parent = os.path.dirname(path) or "."
    if root is not None:
        _make_contained_directories(parent, root, "atomic artifact")
        parent_descriptor, leaf = _contained_open_target(
            path, root, "atomic artifact"
        )
        temporary_leaf: Optional[str] = None
        try:
            _reject_symlink_destination_at(parent_descriptor, leaf, path)
            descriptor, temporary_leaf = _create_regular_temporary_at(
                parent_descriptor, leaf, suffix=".tmp"
            )
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fchmod(handle.fileno(), mode)
                os.fsync(handle.fileno())
            os.replace(
                temporary_leaf,
                leaf,
                src_dir_fd=parent_descriptor,
                dst_dir_fd=parent_descriptor,
            )
            temporary_leaf = None
            _fsync_directory_descriptor(parent_descriptor)
        finally:
            if temporary_leaf is not None:
                try:
                    os.unlink(temporary_leaf, dir_fd=parent_descriptor)
                except FileNotFoundError:
                    pass
            os.close(parent_descriptor)
        return

    os.makedirs(parent, exist_ok=True)
    _reject_symlink_destination(path)
    descriptor, temporary = tempfile.mkstemp(
        prefix=".%s." % os.path.basename(path), suffix=".tmp", dir=parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
        _fsync_directory(parent)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def atomic_write_text(
    path: str,
    text: str,
    *,
    encoding: str = "utf-8",
    mode: int = 0o644,
    root: Optional[str] = None,
) -> None:
    """Durably replace ``path`` with one complete text document."""
    atomic_write_bytes(path, text.encode(encoding), mode=mode, root=root)


def atomic_write_json(
    path: str,
    payload: Any,
    *,
    indent: int = 2,
    ensure_ascii: bool = False,
    sort_keys: bool = False,
    mode: int = 0o644,
    root: Optional[str] = None,
) -> None:
    """Serialize strict JSON and publish it with one durable rename."""
    rendered = json.dumps(
        payload,
        indent=indent,
        ensure_ascii=ensure_ascii,
        sort_keys=sort_keys,
        allow_nan=False,
        default=_json_default,
    )
    atomic_write_text(path, rendered + "\n", mode=mode, root=root)


def publish_bytes_idempotent(
    path: str,
    data: bytes,
    *,
    mode: int = 0o644,
    root: Optional[str] = None,
) -> bool:
    """Create ``path`` once, or accept an already identical artifact.

    The hard-link publication is an atomic create-if-absent operation.  A
    retry after interruption can therefore fill missing siblings while a
    conflicting pre-existing artifact always fails closed.  ``True`` means
    this call published the file; ``False`` means the identical file already
    existed.
    """
    if not isinstance(data, bytes):
        raise TypeError("publish_bytes_idempotent data must be bytes")
    parent = os.path.dirname(path) or "."
    if root is not None:
        _make_contained_directories(parent, root, "published artifact")
        parent_descriptor, leaf = _contained_open_target(
            path, root, "published artifact"
        )
        temporary_leaf: Optional[str] = None
        try:
            _reject_symlink_destination_at(parent_descriptor, leaf, path)
            try:
                existing = _read_regular_bytes_at(
                    parent_descriptor,
                    leaf,
                    path=path,
                    label="published artifact",
                )
            except FileNotFoundError:
                pass
            else:
                if existing != data:
                    raise FileExistsError(
                        "refusing to replace non-identical artifact %s" % path
                    )
                return False

            descriptor, temporary_leaf = _create_regular_temporary_at(
                parent_descriptor, leaf, suffix=".publish"
            )
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fchmod(handle.fileno(), mode)
                os.fsync(handle.fileno())
            try:
                os.link(
                    temporary_leaf,
                    leaf,
                    src_dir_fd=parent_descriptor,
                    dst_dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
                published = True
            except FileExistsError:
                _reject_symlink_destination_at(parent_descriptor, leaf, path)
                existing = _read_regular_bytes_at(
                    parent_descriptor,
                    leaf,
                    path=path,
                    label="published artifact",
                )
                if existing != data:
                    raise FileExistsError(
                        "refusing to replace non-identical artifact %s" % path
                    )
                published = False
            return published
        finally:
            if temporary_leaf is not None:
                try:
                    os.unlink(temporary_leaf, dir_fd=parent_descriptor)
                except FileNotFoundError:
                    pass
                _fsync_directory_descriptor(parent_descriptor)
            os.close(parent_descriptor)

    os.makedirs(parent, exist_ok=True)
    _reject_symlink_destination(path)
    if os.path.lexists(path):
        existing = _read_regular_bytes(path)
        if existing != data:
            raise FileExistsError(
                "refusing to replace non-identical artifact %s" % path
            )
        return False

    descriptor, temporary = tempfile.mkstemp(
        prefix=".%s." % os.path.basename(path), suffix=".publish", dir=parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        try:
            os.link(temporary, path)
            published = True
            _fsync_directory(parent)
        except FileExistsError:
            _reject_symlink_destination(path)
            existing = _read_regular_bytes(path)
            if existing != data:
                raise FileExistsError(
                    "refusing to replace non-identical artifact %s" % path
                )
            published = False
        return published
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def publish_text_idempotent(
    path: str,
    value: str,
    *,
    encoding: str = "utf-8",
    mode: int = 0o644,
    root: Optional[str] = None,
) -> bool:
    """Create one text artifact, accepting only a byte-identical retry."""
    return publish_bytes_idempotent(
        path, value.encode(encoding), mode=mode, root=root
    )


def _strict_json_equal(left: Any, right: Any) -> bool:
    """Compare JSON values without Python's bool/int or int/float coercion."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(
            _strict_json_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _strict_json_equal(a, b) for a, b in zip(left, right)
        )
    return bool(left == right)


def publish_json_idempotent(
    path: str,
    payload: Any,
    *,
    indent: int = 2,
    ensure_ascii: bool = False,
    sort_keys: bool = False,
    mode: int = 0o644,
    root: Optional[str] = None,
) -> bool:
    """Create strict JSON once, or accept an equivalent completed retry."""
    rendered = json.dumps(
        payload,
        indent=indent,
        ensure_ascii=ensure_ascii,
        sort_keys=sort_keys,
        allow_nan=False,
        default=_json_default,
    ) + "\n"
    if root is None:
        _reject_symlink_destination(path)
        exists = os.path.lexists(path)
    else:
        try:
            existing_bytes = _read_regular_bytes(
                path, root=root, label="published JSON artifact"
            )
        except FileNotFoundError:
            exists = False
        else:
            exists = True
    if exists:
        try:
            document = (
                existing_bytes
                if root is not None
                else _read_regular_bytes(path)
            )
            existing = strict_json_loads(document.decode("utf-8"))
        except (OSError, UnicodeError, ValueError) as exc:
            raise FileExistsError(
                "refusing to replace unreadable JSON artifact %s" % path
            ) from exc
        expected = strict_json_loads(rendered)
        if not _strict_json_equal(existing, expected):
            raise FileExistsError(
                "refusing to replace non-identical JSON artifact %s" % path
            )
        return False
    return publish_text_idempotent(path, rendered, mode=mode, root=root)


def unlink_regular_file(
    path: str,
    *,
    root: Optional[str] = None,
    label: str = "artifact",
) -> None:
    """Unlink a regular file through its retained, root-anchored parent."""
    if root is None:
        descriptor = open_regular_read_descriptor(path, label=label)
        os.close(descriptor)
        os.unlink(path)
        _fsync_directory(os.path.dirname(path) or ".")
        return

    parent_descriptor, leaf = _contained_open_target(path, root, label)
    try:
        descriptor = os.open(
            leaf,
            os.O_RDONLY
            | (os.O_NOFOLLOW if hasattr(os, "O_NOFOLLOW") else 0)
            | (os.O_NONBLOCK if hasattr(os, "O_NONBLOCK") else 0)
            | (os.O_CLOEXEC if hasattr(os, "O_CLOEXEC") else 0),
            dir_fd=parent_descriptor,
        )
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ValueError("%s must be a regular file: %s" % (label, path))
        finally:
            os.close(descriptor)
        os.unlink(leaf, dir_fd=parent_descriptor)
        _fsync_directory_descriptor(parent_descriptor)
    finally:
        os.close(parent_descriptor)


def write_manifest(
    path: str,
    payload: Dict[str, Any],
    *,
    root: Optional[str] = None,
) -> Dict[str, Any]:
    """Atomically write a run manifest next to the data and return it."""
    manifest = dict(payload)
    manifest.update(
        {
            "written_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "python": sys.version,
            "platform": platform.platform(),
            "git_commit": _git_commit(),
        }
    )
    atomic_write_json(path, manifest, root=root)
    return manifest
