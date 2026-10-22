"""Content digests of run inputs.

A bundle records what it was computed from, not where it happened to live.
Hashing a directory walks it in sorted order and mixes the relative path into
the digest, so moving a tree does not change its identity but renaming a file
inside it does.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK = 1 << 20


def _hash_file(path: Path, digest: "hashlib._Hash") -> None:
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(chunk)


def digest_path(path: Path) -> str:
    """Return ``sha256:<hex>`` for a file or an unpacked directory tree."""
    path = Path(path)
    digest = hashlib.sha256()
    if path.is_dir():
        entries = sorted(item for item in path.rglob("*") if item.is_file())
        for entry in entries:
            digest.update(entry.relative_to(path).as_posix().encode("utf-8"))
            digest.update(b"\0")
            _hash_file(entry, digest)
            digest.update(b"\0")
    else:
        _hash_file(path, digest)
    return f"sha256:{digest.hexdigest()}"
