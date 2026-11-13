"""Descriptor-relative bounded I/O for broker-owned trees; no symlink traversal."""

from __future__ import annotations

import hashlib
import os
import stat
import uuid
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from .policy_store import StateError

LIMIT = 6_000_000


def relative(value: str) -> tuple[str, ...]:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or "\x00" in value
        or value.startswith("/")
        or any(p in {"", ".", ".."} for p in value.split("/"))
    ):
        raise StateError("Unsafe broker-relative path.")
    return PurePosixPath(value).parts


@contextmanager
def parent(root: Path, name: str, *, create: bool = False):
    parts = relative(name)
    root = Path(root).absolute()
    if any(path.is_symlink() for path in (root, *root.parents)):
        raise StateError("Symlink broker root refused.")
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd, parts[-1]
    finally:
        os.close(fd)


def read(root: Path, name: str, *, limit: int = LIMIT) -> bytes:
    with parent(root, name) as (directory, leaf):
        fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(fd, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise StateError("Broker input must be a regular file.")
            data = stream.read(limit + 1)
            if len(data) > limit:
                raise StateError("Broker input too large.")
            return data


def write(root: Path, name: str, data: bytes, *, expected: str | None = None) -> str:
    """Create exclusively or compare-and-replace exact known bytes. No delete API."""
    if not isinstance(data, bytes) or len(data) > LIMIT:
        raise StateError("Invalid/oversized broker output.")
    with parent(root, name, create=True) as (directory, leaf):
        if expected is None:
            fd = os.open(
                leaf, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600, dir_fd=directory
            )
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        else:
            old = read(root, name)
            if hashlib.sha256(old).hexdigest() != expected:
                raise StateError("Broker input changed; prior bytes retained.")
            temporary = ".policy-" + uuid.uuid4().hex
            fd = os.open(
                temporary,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory,
            )
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, leaf, src_dir_fd=directory, dst_dir_fd=directory)
            finally:
                try:
                    os.unlink(temporary, dir_fd=directory)
                except FileNotFoundError:
                    pass
        os.fsync(directory)
    return hashlib.sha256(data).hexdigest()
