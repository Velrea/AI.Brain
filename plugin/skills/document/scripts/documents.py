"""The document skill's file work: filing a document into the Brain folder's
`documents/`, listing a folder of it, and checking it against what is
recorded. Standard library only, with the core module beside it in the plugin.

A filed document is a file at a path inside `documents/`, with its sha256,
copied or moved there, and recorded afterwards as an entry of type `document`
naming both in its details. A path, once filed, keeps its contents: filing the
same contents there again returns it as it is, and filing others there is
refused, so a pointer to a document never comes to point at something else.
Contents a document entry already names are refused wherever they would be
filed, found through the core module's search, so a document is filed once.
A file already inside `documents/` is never filed again: the user may edit,
move, add, or delete files there by hand, and checking finds each such change
for the entries to record.

Each command prints one JSON object; a failure prints its message to stderr
and exits 1.

    documents.py store --brain <folder> --data <folder> <file> <path> [--move]
    documents.py list --brain <folder> [<path>]
    documents.py check --brain <folder> --data <folder> [<path>]
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

# The plugin's own folder, so the core module and the server's folders are importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from brain.index import IndexUnavailable  # noqa: E402
from brain.read import CEILING, Reader, TooManyHits  # noqa: E402
from server.folders import FolderError, data_dir  # noqa: E402

DOCUMENT = "document"
"""The type of the entry that records a filed document."""

DOCUMENTS_DIR = "documents"
"""The folder, beside `events/` in the Brain folder, that holds the filed documents."""

# Characters a file name cannot hold on every system a sync service may carry
# the folder to, and the names Windows keeps for devices.
_FORBIDDEN = re.compile(r'[<>:"\\|?*\x00-\x1f]')
_RESERVED = re.compile(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?")


class DocumentError(ValueError):
    """A document that cannot be filed as asked."""


class Documents:
    """Files documents into one Brain folder's `documents/`, and lists them.

    Given a `reader`, filing refuses contents a document entry already names,
    and checking compares the documents with the entries.
    """

    def __init__(self, brain_dir: Path, reader: Reader | None = None):
        brain_dir = Path(brain_dir)
        if not brain_dir.is_dir():
            # A sync folder that is not mounted must not quietly become a new, empty Brain.
            raise DocumentError(f"the Brain folder {str(brain_dir)!r} does not exist: is its sync folder available?")
        self.root = brain_dir.resolve() / DOCUMENTS_DIR
        self.reader = reader

    def store(self, source: Path, path: str, *, move: bool = False) -> dict:
        """Copies the file at `source` to `path` inside `documents/`, removing
        `source` once it is filed when `move`, and returns
        `{"path": path, "sha256": ...}`.

        `path` is relative, with `/` between folders, which are created as
        needed. Raises DocumentError for a source that is not a file, a path
        that is not one, a path that already holds other contents, contents a
        document entry already names, and a source already inside
        `documents/`, which filing would copy or, moved, leave the entries
        naming it pointing at nothing. A source that cannot be removed raises
        DocumentError too, after the document is filed, with its path and
        sha256.
        """
        source = Path(source)
        if not source.is_file():
            raise DocumentError(f"no file is at {str(source)!r}")
        target = self.root.joinpath(*_parts(path))
        if source.resolve().is_relative_to(self.root):
            filed = source.resolve().relative_to(self.root).as_posix()
            raise DocumentError(
                f"{str(source)!r} is already in the Brain's documents, at {filed!r}, and is never filed again:"
                f" check it to find what changed since it was recorded"
            )
        if self.reader is not None:
            self._unrecorded(sha256(source))
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

    def check(self, path: str = "") -> dict:
        """How the documents at `path` inside `documents/`, a folder or one
        document, every one when empty, differ from what the document entries
        record, as `{"changed": [...], "moved": [...], "missing": [...], "unrecorded": [...]}`,
        each in path order:

        - changed, `{"path", "entry", "sha256"}`: a document whose contents are
          not the ones its entry names, with their sha256 now;
        - moved, `{"entry", "from", "to"}`: an entry whose document is gone from
          its path, with the same contents at a path no entry names;
        - missing, `{"path", "entry"}`: an entry whose document is gone, its
          contents nowhere checked;
        - unrecorded, `{"path", "sha256"}`: a document no entry names.

        Every document checked is read whole, to hash it. Names starting with a
        dot, as a copy in progress is, are left out. Raises DocumentError for a
        path neither filed nor named by an entry.
        """
        if self.reader is None:
            raise DocumentError("checking needs the recorded entries to compare with")
        prefix = "/".join(_parts(path)) if path else ""
        base = self.root.joinpath(*prefix.split("/")) if prefix else self.root

        def within(name: str) -> bool:
            return not prefix or name == prefix or name.startswith(prefix + "/")

        found = {}
        if base.is_file():
            found[prefix] = sha256(base)
        elif base.is_dir():
            for folder, folders, files in os.walk(base):
                folders[:] = [name for name in folders if not name.startswith(".")]
                for name in files:
                    if not name.startswith("."):
                        file = Path(folder, name)
                        found[file.relative_to(self.root).as_posix()] = sha256(file)
        recorded = {}
        for record in self._documents():
            named = record["details"].get("path")
            if isinstance(named, str) and within(named):
                recorded[named] = (record["id"], record["details"].get("sha256"))
        if prefix and not found and not recorded:
            raise DocumentError(f"nothing is filed at {prefix!r}, and no document entry names it")

        changed = [{"path": name, "entry": entry, "sha256": found[name]}
                   for name, (entry, digest) in recorded.items() if name in found and found[name] != digest]
        unrecorded = {name: digest for name, digest in found.items() if name not in recorded}
        moved, missing = [], []
        for name, (entry, digest) in recorded.items():
            if name in found:
                continue
            to = next((other for other in sorted(unrecorded) if unrecorded[other] == digest), None)
            if to is None:
                missing.append({"path": name, "entry": entry})
            else:
                moved.append({"entry": entry, "from": name, "to": to})
                del unrecorded[to]
        return {
            "changed": sorted(changed, key=lambda item: item["path"]),
            "moved": sorted(moved, key=lambda item: item["from"]),
            "missing": sorted(missing, key=lambda item: item["path"]),
            "unrecorded": [{"path": name, "sha256": unrecorded[name]} for name in sorted(unrecorded)],
        }

    def _documents(self) -> list[dict]:
        """Every document entry, read whole: found by event-date ranges where
        one search would pass the ceiling. Raises DocumentError when one date
        alone does."""
        try:
            hits = self.reader.search(types=[DOCUMENT])
        except TooManyHits as many:
            hits = []
            for start, end, count in many.ranges:
                if count > CEILING:
                    raise DocumentError(
                        f"{count} document entries share the event date {start}, more than one search returns,"
                        f" so the documents cannot be checked against them"
                    ) from many
                hits += self.reader.search(types=[DOCUMENT], event_date_from=start, event_date_to=end)
        return self.reader.read([hit.id for hit in hits])

    def _unrecorded(self, digest: str) -> None:
        """Raises DocumentError when a document entry already names these contents."""
        hits = self.reader.search(types=[DOCUMENT], details={"sha256": digest})
        if not hits:
            return
        records = self.reader.read([hit.id for hit in hits])
        paths = sorted({record["details"].get("path", "?") for record in records})
        named = "; ".join(f"{record['id']} ({record['description']})" for record in records)
        raise DocumentError(
            f"these contents are already filed at {', '.join(map(repr, paths))}, recorded by {named}:"
            f" nothing was filed, and the original is where it was"
        )


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
    storing = commands.add_parser("store")
    storing.add_argument("--brain", type=Path, required=True)
    storing.add_argument("--data", default="")
    storing.add_argument("file", type=Path)
    storing.add_argument("path")
    storing.add_argument("--move", action="store_true")
    listing = commands.add_parser("list")
    listing.add_argument("--brain", type=Path, required=True)
    listing.add_argument("path", nargs="?", default="")
    checking = commands.add_parser("check")
    checking.add_argument("--brain", type=Path, required=True)
    checking.add_argument("--data", default="")
    checking.add_argument("path", nargs="?", default="")
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            result = Documents(args.brain).browse(args.path)
        else:
            # The same plugin data folder, and so the same index, the server reads.
            data, _ = data_dir(args.brain.resolve(), {"BRAIN_DATA_DIR": args.data})
            documents = Documents(args.brain, Reader(args.brain, data))
            if args.command == "store":
                result = documents.store(args.file, args.path, move=args.move)
            else:
                result = documents.check(args.path)
    except (DocumentError, FolderError, IndexUnavailable, TooManyHits, OSError) as error:
        print(error, file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
