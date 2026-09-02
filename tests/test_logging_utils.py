import json
import os

import pytest

import src.logging_utils as logging_utils
from src.logging_utils import (
    JsonlWriter,
    atomic_write_bytes,
    atomic_write_json,
    atomic_write_text,
    publish_bytes_idempotent,
    publish_json_idempotent,
    read_jsonl,
)


def test_atomic_write_json_replaces_complete_document(tmp_path):
    path = tmp_path / "artifact.json"
    atomic_write_json(str(path), {"version": 1, "ok": True})
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "version": 1,
        "ok": True,
    }
    atomic_write_json(str(path), {"version": 2, "ok": False})
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "version": 2,
        "ok": False,
    }
    assert not list(tmp_path.glob("*.tmp"))


def test_root_anchored_atomic_writers_publish_below_root(tmp_path):
    root = tmp_path / "root"
    output = root / "nested"
    root.mkdir()

    atomic_write_bytes(
        str(output / "artifact.bin"), b"bytes", root=str(root)
    )
    atomic_write_text(
        str(output / "artifact.txt"), "text", root=str(root)
    )
    atomic_write_json(
        str(output / "artifact.json"), {"safe": True}, root=str(root)
    )

    assert (output / "artifact.bin").read_bytes() == b"bytes"
    assert (output / "artifact.txt").read_text(encoding="utf-8") == "text"
    assert json.loads((output / "artifact.json").read_text(encoding="utf-8")) == {
        "safe": True
    }


def test_root_anchored_atomic_write_rejects_symlinked_ancestor(tmp_path):
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "linked").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlinked"):
        atomic_write_json(
            str(root / "linked" / "artifact.json"),
            {"safe": False},
            root=str(root),
        )

    assert list(outside.iterdir()) == []


def test_root_anchored_atomic_write_retains_parent_across_ancestor_swap(
    tmp_path, monkeypatch
):
    root = tmp_path / "root"
    output = root / "output"
    detached = root / "detached-output"
    outside = tmp_path / "outside"
    output.mkdir(parents=True)
    outside.mkdir()
    real_replace = logging_utils.os.replace
    swapped = False

    def swap_then_replace(source, destination, *args, **kwargs):
        nonlocal swapped
        if not swapped and kwargs.get("src_dir_fd") is not None:
            output.rename(detached)
            output.symlink_to(outside, target_is_directory=True)
            swapped = True
        return real_replace(source, destination, *args, **kwargs)

    monkeypatch.setattr(logging_utils.os, "replace", swap_then_replace)
    atomic_write_json(
        str(output / "artifact.json"), {"safe": True}, root=str(root)
    )

    assert swapped
    assert list(outside.iterdir()) == []
    assert json.loads(
        (detached / "artifact.json").read_text(encoding="utf-8")
    ) == {"safe": True}


def test_idempotent_json_publish_accepts_equivalent_retry(tmp_path):
    path = tmp_path / "artifact.json"
    path.write_text('{"ok":true,"value":3}', encoding="utf-8")
    assert publish_json_idempotent(
        str(path), {"ok": True, "value": 3}
    ) is False
    assert path.read_text(encoding="utf-8") == '{"ok":true,"value":3}'


def test_idempotent_publish_rejects_conflicting_retry(tmp_path):
    path = tmp_path / "artifact.bin"
    assert publish_bytes_idempotent(str(path), b"first") is True
    assert publish_bytes_idempotent(str(path), b"first") is False
    with pytest.raises(FileExistsError, match="non-identical"):
        publish_bytes_idempotent(str(path), b"second")
    assert path.read_bytes() == b"first"


def test_idempotent_json_publish_rejects_type_coercion(tmp_path):
    path = tmp_path / "artifact.json"
    path.write_text('{"count": true}', encoding="utf-8")
    with pytest.raises(FileExistsError, match="non-identical"):
        publish_json_idempotent(str(path), {"count": 1})


def test_writers_reject_symlink_destinations(tmp_path):
    target = tmp_path / "target.json"
    target.write_text('{"safe": true}', encoding="utf-8")
    link = tmp_path / "artifact.json"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        atomic_write_json(str(link), {"safe": False})
    with pytest.raises(ValueError, match="symlink"):
        publish_json_idempotent(str(link), {"safe": True})
    assert json.loads(target.read_text(encoding="utf-8")) == {"safe": True}


def test_jsonl_writer_leaves_a_complete_resumable_prefix(tmp_path):
    path = tmp_path / "records.jsonl"
    with JsonlWriter(str(path), validate=False) as writer:
        writer.write({"coordinate": 0})
        writer.write({"coordinate": 1})
    assert list(read_jsonl(str(path))) == [
        {"coordinate": 0},
        {"coordinate": 1},
    ]


def test_jsonl_io_rejects_symlinks_and_special_files(tmp_path):
    target = tmp_path / "target.jsonl"
    target.write_text('{"safe": true}\n', encoding="utf-8")
    link = tmp_path / "link.jsonl"
    link.symlink_to(target)

    with pytest.raises(ValueError, match="symlink"):
        JsonlWriter(str(link), validate=False)
    with pytest.raises(ValueError, match="symlink"):
        list(read_jsonl(str(link)))

    fifo = tmp_path / "records.fifo"
    os.mkfifo(fifo)
    with pytest.raises(ValueError, match="regular file"):
        JsonlWriter(str(fifo), validate=False)
    with pytest.raises(ValueError, match="regular file"):
        list(read_jsonl(str(fifo)))


def test_jsonl_reader_enforces_root_and_rejects_symlinked_components(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_log = outside / "records.jsonl"
    outside_log.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="canonical root"):
        list(read_jsonl(str(outside_log), root=str(root)))

    (root / "linked").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlinks"):
        list(read_jsonl(str(root / "linked" / "records.jsonl"), root=str(root)))

    with pytest.raises(ValueError, match="canonical root"):
        JsonlWriter(
            str(outside / "new" / "records.jsonl"),
            validate=False,
            root=str(root),
        )
    assert not (outside / "new").exists()

    with pytest.raises(ValueError, match="symlinked"):
        JsonlWriter(
            str(root / "linked" / "new" / "records.jsonl"),
            validate=False,
            root=str(root),
        )
    assert not (outside / "new").exists()


def test_jsonl_writer_keeps_verified_descriptor_after_path_replacement(tmp_path):
    path = tmp_path / "records.jsonl"
    opened_file = tmp_path / "opened.jsonl"
    unrelated = tmp_path / "unrelated.jsonl"
    unrelated.write_text('{"untouched": true}\n', encoding="utf-8")

    writer = JsonlWriter(str(path), validate=False)
    os.replace(path, opened_file)
    path.symlink_to(unrelated)
    try:
        writer.write({"coordinate": 1})
    finally:
        writer.close()

    assert list(read_jsonl(str(opened_file))) == [{"coordinate": 1}]
    assert unrelated.read_text(encoding="utf-8") == '{"untouched": true}\n'


@pytest.mark.parametrize(
    "document, message",
    [
        ('{"coordinate": 1, "coordinate": 2}\n', "duplicate"),
        ('{"coordinate": NaN}\n', "non-finite"),
        ('{"coordinate": Infinity}\n', "non-finite"),
        ('{"coordinate": -Infinity}\n', "non-finite"),
        ('{"coordinate": 1e999}\n', "non-finite"),
    ],
)
def test_read_jsonl_rejects_non_strict_json(tmp_path, document, message):
    path = tmp_path / "records.jsonl"
    path.write_text(document, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        list(read_jsonl(str(path)))


def test_json_serialization_rejects_arbitrary_string_fallback(tmp_path):
    class Unsupported:
        def __str__(self):
            return "must-not-be-stringified"

    jsonl_path = tmp_path / "records.jsonl"
    with JsonlWriter(str(jsonl_path), validate=False) as writer:
        with pytest.raises(TypeError, match="not JSON serializable"):
            writer.write({"value": Unsupported()})
    assert jsonl_path.read_bytes() == b""

    with pytest.raises(TypeError, match="not JSON serializable"):
        atomic_write_json(str(tmp_path / "artifact.json"), {"value": Unsupported()})
