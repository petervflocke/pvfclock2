"""Atomic YAML storage with a stable, per-user runtime lock (Linux)."""
from contextlib import contextmanager
from collections.abc import Iterator
from hashlib import sha256
from pathlib import Path
import fcntl
import os
import tempfile

import yaml


@contextmanager
def config_lock(path: Path) -> Iterator[None]:
    directory = Path(tempfile.gettempdir()) / f"pvfclock2-locks-{os.getuid()}"
    directory.mkdir(mode=0o700, exist_ok=True)
    if directory.is_symlink() or directory.stat().st_uid != os.getuid():
        raise PermissionError("Unsafe configuration lock directory")
    name = sha256(str(path.resolve()).encode()).hexdigest()
    with (directory / name).open("a") as lock:
        # Never wait on another process from a Qt callback; retry on the next tick.
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            yaml.safe_dump(data, stream, sort_keys=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def apply_changes(current: dict, original: dict, edited: dict) -> None:
    """Apply only local changes, preserving unrelated fresh on-disk edits."""
    for key, value in edited.items():
        if key in original and value == original[key]:
            continue
        if isinstance(value, dict) and isinstance(original.get(key), dict) and isinstance(current.get(key), dict):
            apply_changes(current[key], original[key], value)
        else:
            current[key] = value
    for key in original.keys() - edited.keys():
        current.pop(key, None)
