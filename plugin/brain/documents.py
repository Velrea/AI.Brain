"""The documents store: copies of original files, kept in the Brain folder.

A filed document is a copy of the file at a path inside `documents/`, with
its sha256. A path, once filed, keeps its contents: filing the same contents
there again returns it as it is, and filing others there is refused, so a
pointer to a document never comes to point at something else.
"""

import contextlib
import hashlib
import os
import re
import shutil
import uuid
from collections.abc import Mapping
from pathlib import Path

from .format import documents_dir

# Characters a file name cannot hold on every system a sync service may carry
# the folder to, and the names Windows keeps for devices.
_FORBIDDEN = re.compile(r'[<>:"\\|?*\x00-\x1f]')
_RESERVED = re.compile(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?")
_SHA256 = re.compile(r"[0-9a-f]{64}")


class DocumentError(ValueError):
    """A document that cannot be filed as asked."""


class Documents:
    """Files documents into one Brain folder's `documents/`."""

    def __init__(self, brain_dir: Path):
        self.root = documents_dir(Path(brain_dir).resolve())

    def store(self, source: Path, path: str) -> dict:
        """Copies the file at `source` to `path` inside `documents/`, and returns
        `{"path": path, "sha256": ...}`.

        `path` is relative, with `/` between folders, such as
        `car/2026-09-14 oil change invoice.pdf`. Its folders are created as
        needed. Raises DocumentError for a source that is not a file, a path
        that is not one, or a path that already holds other contents.
        """
        source = Path(source)
        if not source.is_file():
            raise DocumentError(f"no file is at {str(source)!r}")
        target = self.root.joinpath(*_parts(path))
        target.parent.mkdir(parents=True, exist_ok=True)
        # Copied beside the target and renamed into place, so a sync service
        # never carries a part-written document.
        temp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
        try:
            digest = _copy(source, temp)
            if target.exists():
                if not target.is_file() or _sha256(target) != digest:
                    raise DocumentError(
                        f"{path!r} already holds a different document: file this one at a path of its own"
                    )
            else:
                os.replace(temp, target)
        finally:
            with contextlib.suppress(FileNotFoundError):
                temp.unlink()
        return {"path": path, "sha256": digest}


def reference(document: object) -> dict:
    """A filed document as an entry names it, `{"path": ..., "sha256": ...}`,
    the shape `Documents.store` returns, each part checked."""
    if not isinstance(document, Mapping) or set(document) != {"path", "sha256"}:
        raise DocumentError('a document is named by {"path": ..., "sha256": ...}, as filing it returned')
    _parts(document["path"])
    if not isinstance(document["sha256"], str) or not _SHA256.fullmatch(document["sha256"]):
        raise DocumentError(f"a document's sha256 is 64 lowercase hex characters: {document['sha256']!r}")
    return {"path": document["path"], "sha256": document["sha256"]}


def _parts(path: object) -> list[str]:
    if not isinstance(path, str) or not path.strip():
        raise DocumentError("a document's path must be non-empty text")
    parts = path.split("/")
    for part in parts:
        if (
            part in ("", ".", "..")
            or part != part.strip()
            or part.endswith(".")
            or _FORBIDDEN.search(part)
            or _RESERVED.fullmatch(part)
        ):
            raise DocumentError(
                f"a document's path is relative, with / between folders, and no name in it empty,"
                f" . or .., ending in a dot or a space, or holding any of <>:\"\\|?*: {path!r}"
            )
    return parts


def _copy(source: Path, target: Path) -> str:
    """Copies `source` to `target`, synced to disk, and returns its sha256."""
    digest = hashlib.sha256()
    with open(source, "rb") as reading, open(target, "xb") as writing:
        while chunk := reading.read(1 << 20):
            digest.update(chunk)
            writing.write(chunk)
        writing.flush()
        os.fsync(writing.fileno())
    # Keeps the original's modified time where the folder allows it.
    with contextlib.suppress(OSError):
        shutil.copystat(source, target)
    return digest.hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as reading:
        while chunk := reading.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()
