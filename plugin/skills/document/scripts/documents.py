"""The document skill's file work: hashing a document, filing it into the Brain
folder's `documents/`, and listing a folder of it. Standard library only.

A filed document is a file at a path inside `documents/`, with its sha256,
copied or moved there, and recorded afterwards as an entry of type `document`
naming both in its details. A path, once filed, keeps its contents: filing the
same contents there again returns it as it is, and filing others there is
refused, so a pointer to a document never comes to point at something else.

Each command prints one JSON object; a failure prints its message to stderr
and exits 1.

    documents.py hash <file>
    documents.py store --brain <folder> <file> <path> [--move]
    documents.py list --brain <folder> [<path>]
"""

import argparse
import contextlib
import hashlib
import json
import os
import re
import shutil
import sys
import uuid
from pathlib import Path

DOCUMENTS_DIR = "documents"
"""The folder, beside `events/` in the Brain folder, that holds the filed documents."""

# Characters a file name cannot hold on every system a sync service may carry
# the folder to, and the names Windows keeps for devices.
_FORBIDDEN = re.compile(r'[<>:"\\|?*\x00-\x1f]')
_RESERVED = re.compile(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?")


class DocumentError(ValueError):
    """A document that cannot be filed as asked."""


class Documents:
    """Files documents into one Brain folder's `documents/`, and lists them."""

    def __init__(self, brain_dir: Path):
        brain_dir = Path(brain_dir)
        if not brain_dir.is_dir():
            # A sync folder that is not mounted must not quietly become a new, empty Brain.
            raise DocumentError(f"the Brain folder {str(brain_dir)!r} does not exist: is its sync folder available?")
        self.root = brain_dir.resolve() / DOCUMENTS_DIR

    def store(self, source: Path, path: str, *, move: bool = False) -> dict:
        """Copies the file at `source` to `path` inside `documents/`, removing
        `source` once it is filed when `move`, and returns
        `{"path": path, "sha256": ...}`.

        `path` is relative, with `/` between folders, which are created as
        needed. Raises DocumentError for a source that is not a file, a path
        that is not one, a path that already holds other contents, and a move
        of a document already filed, which would leave the entries naming it
        pointing at nothing. A source that cannot be removed raises
        DocumentError too, after the document is filed, with its path and sha256.
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
        target.parent.mkdir(parents=True, exist_ok=True)
        # Copied beside the target and renamed into place, so a sync service
        # never carries a part-written document.
        temp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
        try:
            digest = _copy(source, temp)
            if target.exists():
                if not target.is_file() or sha256(target) != digest:
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
                    f" removed ({error.strerror}): record the document by that path and sha256, and tell the"
                    f" user the original is still there"
                ) from error
        return {"path": path, "sha256": digest}

    def browse(self, folder: str = "") -> dict:
        """The folders and documents directly inside `folder` of `documents/`,
        the top when empty, as `{"folders": [{"name", "documents"}], "documents": [...]}`,
        each folder with how many documents it holds at any depth, in name order.

        Names starting with a dot, as a copy in progress is, are left out.
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as reading:
        while chunk := reading.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


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


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="documents.py")
    commands = parser.add_subparsers(dest="command", required=True)
    hashing = commands.add_parser("hash")
    hashing.add_argument("file", type=Path)
    storing = commands.add_parser("store")
    storing.add_argument("--brain", type=Path, required=True)
    storing.add_argument("file", type=Path)
    storing.add_argument("path")
    storing.add_argument("--move", action="store_true")
    listing = commands.add_parser("list")
    listing.add_argument("--brain", type=Path, required=True)
    listing.add_argument("path", nargs="?", default="")
    args = parser.parse_args(argv)
    try:
        if args.command == "hash":
            if not args.file.is_file():
                raise DocumentError(f"no file is at {str(args.file)!r}")
            result = {"sha256": sha256(args.file)}
        elif args.command == "store":
            result = Documents(args.brain).store(args.file, args.path, move=args.move)
        else:
            result = Documents(args.brain).browse(args.path)
    except (DocumentError, OSError) as error:
        print(error, file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
