"""The documents store: original files, kept in the Brain folder.

A filed document is a file at a path inside `documents/`, with its sha256,
copied or moved there. A path, once filed, keeps its contents: filing the
same contents there again returns it as it is, and filing others there is
refused, so a pointer to a document never comes to point at something else.
Contents an entry already names are refused wherever they would be filed, so
a document is filed once.
"""

import contextlib
import hashlib
import os
import re
import shutil
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from .format import documents_dir

if TYPE_CHECKING:
    from .read import Reader

# Characters a file name cannot hold on every system a sync service may carry
# the folder to, and the names Windows keeps for devices.
_FORBIDDEN = re.compile(r'[<>:"\\|?*\x00-\x1f]')
_RESERVED = re.compile(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?")
_SHA256 = re.compile(r"[0-9a-f]{64}")


class DocumentError(ValueError):
    """A document that cannot be filed as asked."""


class Documents:
    """Files documents into one Brain folder's `documents/`, and lists them.

    Given a `reader`, filing refuses contents an entry already names.
    """

    def __init__(self, brain_dir: Path, reader: "Reader | None" = None):
        self.root = documents_dir(Path(brain_dir).resolve())
        self.reader = reader

    def store(self, source: Path, path: str, *, move: bool = False) -> dict:
        """Copies the file at `source` to `path` inside `documents/`, removing
        `source` once it is filed when `move`, and returns
        `{"path": path, "sha256": ...}`.

        `path` is relative, with `/` between folders, such as
        `assets/blue-hatchback/service/2026-09-14-oil-change-invoice.pdf`. Its
        folders are created as needed. Raises DocumentError for a source that
        is not a file, a path that is not one, a path that already holds other
        contents, contents an entry already names, and a move of a document
        already filed, which would leave the entries naming it pointing at
        nothing. A source that cannot be removed raises DocumentError too,
        after the document is filed, with its path and sha256.
        """
        source = Path(source)
        if not source.is_file():
            raise DocumentError(f"no file is at {str(source)!r}")
        target = self.root.joinpath(*_parts(path))
        if move and source.resolve().is_relative_to(self.root):
            raise DocumentError(
                f"{str(source)!r} is already filed in the Brain's documents, and a filed document is never"
                f" moved: entries point at it where it is"
            )
        if self.reader is not None:
            self._unnamed(_sha256(source))
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
        if move:
            try:
                source.unlink()
            except OSError as error:
                raise DocumentError(
                    f"filed at {path!r} with sha256 {digest}, but the original at {str(source)!r} could not be"
                    f" removed ({error.strerror}): name the document by that path and sha256, and tell the"
                    f" user the original is still there"
                ) from error
        return {"path": path, "sha256": digest}

    def browse(self, folder: str = "") -> dict:
        """The folders and documents directly inside `folder` of `documents/`,
        the top when empty, as `{"folders": [{"name", "documents"}], "documents": [...]}`,
        each folder with how many documents it holds at any depth, in name order.

        Names starting with a dot, such as a copy in progress, are left out.
        Raises DocumentError for a folder that is not filed.
        """
        base = self.root.joinpath(*_parts(folder)) if folder else self.root
        if not base.is_dir():
            if folder:
                raise DocumentError(f"no folder is filed at {folder!r}")
            return {"folders": [], "documents": []}
        folders, documents = [], []
        for child in sorted(base.iterdir(), key=lambda child: child.name.lower()):
            if child.name.startswith("."):
                continue
            if child.is_dir():
                folders.append({"name": child.name, "documents": _count(child)})
            elif child.is_file():
                documents.append(child.name)
        return {"folders": folders, "documents": documents}

    def _unnamed(self, digest: str) -> None:
        """Raises DocumentError when an entry already names these contents."""
        hits = self.reader.search(documents=[digest])
        if not hits:
            return
        records = self.reader.read([hit.id for hit in hits])
        paths = sorted({
            document["path"]
            for record in records
            for document in record["details"].get("documents", [])
            if document.get("sha256") == digest
        })
        named = "; ".join(f"{record['id']} ({record['description']})" for record in records)
        raise DocumentError(
            f"these contents are already filed at {', '.join(map(repr, paths))}, named by {named}:"
            f" nothing was filed, and the original is where it was"
        )


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


def _count(folder: Path) -> int:
    """How many documents `folder` holds at any depth, leaving out dot names."""
    count = 0
    for _, folders, files in os.walk(folder):
        folders[:] = [name for name in folders if not name.startswith(".")]
        count += sum(1 for name in files if not name.startswith("."))
    return count


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as reading:
        while chunk := reading.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()
