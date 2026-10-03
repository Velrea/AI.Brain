"""The local index: a SQLite database this machine keeps of one Brain folder.

The files are the Brain; the index is a projection of them, kept in the
machine's plugin data folder and never synced. It holds nothing the files do not:
missing, corrupt, or built by another version, it is deleted and rebuilt from
them. Every read catches it up first, taking in only the complete lines each
file has gained since, so a sealed file is read once in its life.

A correction is applied once, when it arrives: the index keeps every record,
and each entry as it stands now, with its revisions applied and any entry
merged into it noted.
"""

import contextlib
import functools
import json
import os
import sqlite3
import time
from collections import defaultdict
from collections.abc import Iterable, Iterator
from pathlib import Path

from .format import REVISABLE, brain_key, events_dir, is_event_file

VERSION = 2
"""The index's own layout. A change names a new file, so sessions running two
versions of the plugin never rebuild each other's index."""

BUSY_TIMEOUT = 30.0
"""Seconds a session waits for another to finish taking in a file."""

CACHE_KB = 64 * 1024
"""The most memory, in KiB, a connection's page cache holds."""

READ_RETRY = 10.0
"""Seconds a read of an event file another process holds keeps retrying."""

_TABLES = ("files", "records", "entries", "slugs", "links", "forms", "words")

# Read in this order from `records`, so a row unpacks as a record.
_RECORD = (
    "id, entry, type, version, recorded_at, event_date, description, source, body,"
    " slugs, aliases, links, revises, details"
)

_SCHEMA = (
    # How many bytes of each file are taken in: every complete line before that point.
    "CREATE TABLE IF NOT EXISTS files (name TEXT PRIMARY KEY, offset INTEGER NOT NULL) WITHOUT ROWID",
    # Every record once, as its line holds it, except an original's body, which
    # `entries` keeps. The lists and details are JSON.
    """CREATE TABLE IF NOT EXISTS records (
        id TEXT PRIMARY KEY, entry TEXT NOT NULL, type TEXT NOT NULL, version INTEGER,
        recorded_at TEXT, event_date TEXT NOT NULL, description TEXT NOT NULL, source TEXT,
        body TEXT, slugs TEXT NOT NULL, aliases TEXT NOT NULL, links TEXT NOT NULL,
        revises TEXT NOT NULL, details TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS records_entry ON records (entry)",
    # Every entry as it stands now, by its original's id. `slug` is the slug it was
    # created under; `changed_at` the latest `recorded_at` among its records; `amended`
    # its amendments as plain text; `merged_into` the entry that took its slug, if any.
    """CREATE TABLE IF NOT EXISTS entries (
        rowid INTEGER PRIMARY KEY, id TEXT NOT NULL UNIQUE, slug TEXT, type TEXT NOT NULL,
        version INTEGER, recorded_at TEXT, changed_at TEXT, event_date TEXT NOT NULL,
        description TEXT NOT NULL, source TEXT, body TEXT NOT NULL, slugs TEXT NOT NULL,
        aliases TEXT NOT NULL, links TEXT NOT NULL, details TEXT NOT NULL,
        amendments TEXT NOT NULL, amended TEXT NOT NULL, merged_into TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS entries_order ON entries (event_date, id)",
    "CREATE INDEX IF NOT EXISTS entries_slug ON entries (slug)",
    # A search by name compares only the entries of its types; few entries are ever merged.
    "CREATE INDEX IF NOT EXISTS entries_type ON entries (type) WHERE merged_into IS NULL",
    "CREATE INDEX IF NOT EXISTS entries_merged ON entries (merged_into) WHERE merged_into IS NOT NULL",
    # The slugs each entry carries; `added` marks one a revision added.
    """CREATE TABLE IF NOT EXISTS slugs (
        slug TEXT NOT NULL, id TEXT NOT NULL, added INTEGER NOT NULL, PRIMARY KEY (slug, id)
    ) WITHOUT ROWID""",
    "CREATE INDEX IF NOT EXISTS slugs_id ON slugs (id)",
    # The slugs each entry links to.
    "CREATE TABLE IF NOT EXISTS links (slug TEXT NOT NULL, id TEXT NOT NULL, PRIMARY KEY (slug, id)) WITHOUT ROWID",
    "CREATE INDEX IF NOT EXISTS links_id ON links (id)",
    # Each entry's slugs, aliases, and description, as a search by name compares them.
    "CREATE TABLE IF NOT EXISTS forms (form TEXT NOT NULL, id TEXT NOT NULL, PRIMARY KEY (id, form)) WITHOUT ROWID",
    # Full-text search over each entry's words, kept in step with `entries`.
    """CREATE VIRTUAL TABLE IF NOT EXISTS words USING fts5 (
        description, body, amended, content = 'entries', content_rowid = 'rowid',
        tokenize = 'porter unicode61 remove_diacritics 2'
    )""",
    """CREATE TRIGGER IF NOT EXISTS entries_added AFTER INSERT ON entries BEGIN
        INSERT INTO words (rowid, description, body, amended)
        VALUES (new.rowid, new.description, new.body, new.amended);
    END""",
    """CREATE TRIGGER IF NOT EXISTS entries_removed AFTER DELETE ON entries BEGIN
        INSERT INTO words (words, rowid, description, body, amended)
        VALUES ('delete', old.rowid, old.description, old.body, old.amended);
    END""",
)


class IndexUnavailable(RuntimeError):
    """This Python's SQLite cannot hold the index."""


class FileHeld(OSError):
    """An event file stayed held by another process past the retries, so the index
    could not take it in, and nothing was answered without it."""


class Index:
    """This machine's index of one Brain folder, in its plugin data folder."""

    def __init__(self, brain_dir: Path, data_dir: Path, *, busy_timeout: float = BUSY_TIMEOUT):
        brain_dir = Path(brain_dir).resolve()
        self.events = events_dir(brain_dir)
        self.data_dir = Path(data_dir)
        self.key = brain_key(brain_dir)
        self.path = self.data_dir / f"{self.key}.index-v{VERSION}.sqlite"
        self.busy_timeout = busy_timeout

    @contextlib.contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """A connection to the index, caught up with the files, closed after use."""
        _check_sqlite()
        try:
            con = self._caught_up()
        except sqlite3.DatabaseError as error:
            if getattr(error, "sqlite_errorcode", None) not in (sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB):
                raise
            # Corrupt: the index holds nothing the files do not, so it is built afresh.
            self._delete()
            con = self._caught_up()
        try:
            yield con
        finally:
            con.close()

    def _caught_up(self) -> sqlite3.Connection:
        con = self._open()
        try:
            self._catch_up(con)
        except BaseException:
            con.close()
            raise
        return con

    def _open(self) -> sqlite3.Connection:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        new = not self.path.exists()
        con = sqlite3.connect(self.path, timeout=self.busy_timeout, isolation_level=None)
        try:
            # Sessions read while another takes in a file. The index can be rebuilt, so a
            # commit need not wait for the disk.
            con.execute("PRAGMA journal_mode = WAL")
            con.execute("PRAGMA synchronous = NORMAL")
            # Taking in a file inserts across several B-trees at once; SQLite's 2 MB default thrashes.
            con.execute(f"PRAGMA cache_size = -{CACHE_KB}")
            if con.execute("PRAGMA user_version").fetchone()[0] != VERSION:
                with _transaction(con):
                    for statement in _SCHEMA:
                        con.execute(statement)
                    con.execute(f"PRAGMA user_version = {VERSION}")
        except BaseException:
            con.close()
            raise
        if new:
            self._delete_other_versions()
        return con

    def _catch_up(self, con: sqlite3.Connection) -> None:
        listed = self._listed()
        taken = dict(con.execute("SELECT name, offset FROM files"))
        if _lost(listed, taken):
            with _transaction(con):
                # Another session may have rebuilt it while this one waited.
                if _lost(self._listed(), dict(con.execute("SELECT name, offset FROM files"))):
                    _rebuild(con)
            taken = {}
        for name in sorted(listed):
            if listed[name] > taken.get(name, 0):
                self._take_in(con, name)

    def _listed(self) -> dict[str, int]:
        """Each event file's name and size."""
        try:
            with os.scandir(self.events) as found:
                return {
                    item.name: item.stat().st_size
                    for item in found
                    if is_event_file(item.name) and item.is_file()
                }
        except FileNotFoundError:
            return {}

    def _take_in(self, con: sqlite3.Connection, name: str) -> None:
        """Takes in the complete lines `name` has gained, and moves its offset past them."""
        with _transaction(con):
            # Read under the lock, so two sessions never take in the same lines.
            row = con.execute("SELECT offset FROM files WHERE name = ?", (name,)).fetchone()
            offset = row[0] if row else 0
            data = _read_from(self.events / name, offset)
            if data is None:
                return  # Gone since it was listed; the next read rebuilds.
            end = data.rfind(b"\n") + 1
            if not end:
                return  # Only part of a line so far: a write in progress, or a torn line.
            records = [record for line in data[:end].split(b"\n") if (record := _parse(line))]
            _add(con, records)
            con.execute(
                "INSERT INTO files (name, offset) VALUES (?, ?)"
                " ON CONFLICT (name) DO UPDATE SET offset = excluded.offset",
                (name, offset + end),
            )

    def _delete(self) -> None:
        for suffix in ("", "-wal", "-shm"):
            Path(f"{self.path}{suffix}").unlink(missing_ok=True)

    def _delete_other_versions(self) -> None:
        """Clears the index files older or newer versions left, where no session holds them."""
        for path in self.data_dir.glob(f"{self.key}.index-v*.sqlite*"):
            if not path.name.startswith(self.path.name):
                with contextlib.suppress(OSError):
                    path.unlink()


@functools.cache
def _check_sqlite() -> None:
    con = sqlite3.connect(":memory:")
    try:
        con.execute("SELECT json_extract('{}', '$')")
        con.execute("CREATE VIRTUAL TABLE probe USING fts5 (x, tokenize = 'porter unicode61 remove_diacritics 2')")
    except sqlite3.Error as error:
        raise IndexUnavailable(
            f"this Python's SQLite {sqlite3.sqlite_version} lacks full-text search or JSON,"
            f" which the Brain's index needs: {error}"
        ) from error
    finally:
        con.close()


@contextlib.contextmanager
def _transaction(con: sqlite3.Connection) -> Iterator[None]:
    """One write transaction, holding the index's lock from the start."""
    con.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        con.execute("ROLLBACK")
        raise
    con.execute("COMMIT")


def _read_from(path: Path, offset: int) -> bytes | None:
    """The bytes of `path` past `offset`, or None when it is gone. A file another
    process holds open without sharing it, as a sync service can on Windows, is
    retried with backoff, then raises FileHeld."""
    deadline = time.monotonic() + READ_RETRY
    delay = 0.05
    while True:
        try:
            with open(path, "rb") as file:
                file.seek(offset)
                return file.read()
        except FileNotFoundError:
            return None
        except PermissionError as error:
            if time.monotonic() >= deadline:
                raise FileHeld(
                    f"the event file {path.name} stayed held by another process, such as a sync service, for"
                    f" {READ_RETRY:g} seconds, so the index could not take it in: try again shortly"
                ) from error
            time.sleep(delay)
            delay = min(delay * 2, 1.0)


def _lost(listed: dict[str, int], taken: dict[str, int]) -> bool:
    """Whether a file the index took in has vanished or shrunk. The index cannot tell
    which of its rows came only from that file, so it is rebuilt."""
    return any(name not in listed or listed[name] < offset for name, offset in taken.items())


def _rebuild(con: sqlite3.Connection) -> None:
    for table in _TABLES:
        con.execute(f"DROP TABLE IF EXISTS {table}")
    for statement in _SCHEMA:
        con.execute(statement)


def _parse(line: bytes) -> tuple | None:
    """A record as a row of `records`, or None for a line that is not one: not
    valid JSON, a torn line among them, or missing a field of the envelope."""
    try:
        record = json.loads(line)
    except ValueError:
        return None
    if not isinstance(record, dict):
        return None
    required = [record.get(name) for name in ("id", "entry", "type", "event_date", "description", "body")]
    if not all(isinstance(value, str) for value in required):
        return None
    id, entry, type, event_date, description, body = required
    version, recorded_at, source = (record.get(name) for name in ("version", "recorded_at", "source"))
    details = record.get("details")
    return (
        id, entry, type,
        version if isinstance(version, int) and not isinstance(version, bool) else None,
        recorded_at if isinstance(recorded_at, str) else None,
        event_date, description,
        source if isinstance(source, str) else None,
        body,
        *(_json(_texts(record.get(name))) for name in ("slugs", "aliases", "links", "revises")),
        _json(details if isinstance(details, dict) else {}),
    )


def _add(con: sqlite3.Connection, records: list[tuple]) -> None:
    """Adds records, each id once, and settles every entry they touch."""
    rows, bodies, entries = [], {}, set()
    for record in records:
        id, entry = record[:2]
        entries.add(entry)  # An original's own id, or the entry a revision revises.
        if entry == id:
            # Its body goes to `entries` alone, so the index holds it once.
            bodies.setdefault(id, record[8])
            record = (*record[:8], None, *record[9:])
        rows.append(record)
    con.executemany(f"INSERT OR IGNORE INTO records ({_RECORD}) VALUES ({', '.join('?' * 14)})", rows)
    slugs = _settle_entries(con, sorted(entries), bodies)
    _settle_merges(con, sorted(slugs))


def _settle_entries(con: sqlite3.Connection, ids: list[str], bodies: dict[str, str]) -> set[str]:
    """Rewrites each entry as it stands now: its original with its revisions applied,
    and returns every slug the entries carry.

    A revision is a record whose `entry` names an original of the same type. For
    each field it replaces, the newest revision setting it wins, by id, so two
    machines revising different fields before they sync both hold; each of its
    `details` fields replaces the entry's, a null removing it; its slugs and
    aliases add to the entry's, so two machines adding names lose neither. A
    revision whose original has not arrived waits in `records` until it does.
    `bodies` are the bodies of originals just taken in; an earlier one's is in
    its entry's row.
    """
    if not ids:
        return set()
    wanted = json.dumps(ids)
    bodies = dict(con.execute(
        "SELECT id, body FROM entries WHERE id IN (SELECT value FROM json_each(?))", (wanted,),
    )) | bodies
    originals = {
        row[0]: row for row in con.execute(
            f"SELECT {_RECORD} FROM records WHERE id IN (SELECT value FROM json_each(?)) AND entry = id",
            (wanted,),
        )
    }
    revisions = defaultdict(list)
    for row in con.execute(
        f"SELECT {_RECORD} FROM records WHERE entry IN (SELECT value FROM json_each(?)) AND id != entry"
        " ORDER BY id",
        (wanted,),
    ):
        revisions[row[1]].append(row)
    _remove(con, [(id,) for id in ids])
    rows, slug_rows, link_rows, form_rows, carried = [], [], [], [], set()
    for id in ids:
        original = originals.get(id)
        if original is None:
            continue
        _, _, type, version, recorded_at, event_date, description, source, _, slugs, aliases, links, _, details = original
        slugs, aliases, links, details = json.loads(slugs), json.loads(aliases), json.loads(links), json.loads(details)
        created = list(slugs)
        amendments, changed_at = [], recorded_at
        for revision in revisions[id]:
            r_id, _, r_type, _, r_recorded_at, r_event_date, r_description, _, r_body, *r_lists, r_details = revision
            if r_type != type:
                continue
            r_slugs, r_aliases, r_links, r_revises = map(json.loads, r_lists)
            sets = set(r_revises) & set(REVISABLE)
            if "description" in sets:
                description = r_description
            if "event_date" in sets:
                event_date = r_event_date
            if "links" in sets:
                links = r_links
            slugs += [slug for slug in r_slugs if slug not in slugs]
            aliases += [alias for alias in r_aliases if alias not in aliases]
            for name, value in json.loads(r_details).items():
                if value is None:
                    details.pop(name, None)
                else:
                    details[name] = value
            if r_body.strip():
                amendments.append({"id": r_id, "recorded_at": r_recorded_at, "body": r_body})
            changed_at = max(filter(None, (changed_at, r_recorded_at)), default=None)
        rows.append((
            id, created[0] if created else None, type, version, recorded_at, changed_at, event_date,
            description, source, bodies[id], _json(slugs), _json(aliases), _json(links), _json(details),
            _json(amendments), "\n\n".join(a["body"] for a in amendments),
        ))
        slug_rows += [(slug, id, int(slug not in created)) for slug in slugs]
        link_rows += [(slug, id) for slug in links]
        form_rows += {(form, id) for form in map(plain, [*slugs, *aliases, description]) if form}
        carried.update(slugs)
    con.executemany(
        "INSERT INTO entries (id, slug, type, version, recorded_at, changed_at, event_date, description,"
        " source, body, slugs, aliases, links, details, amendments, amended)"
        f" VALUES ({', '.join('?' * 16)})",
        rows,
    )
    con.executemany("INSERT OR IGNORE INTO slugs (slug, id, added) VALUES (?, ?, ?)", slug_rows)
    con.executemany("INSERT OR IGNORE INTO links (slug, id) VALUES (?, ?)", link_rows)
    con.executemany("INSERT OR IGNORE INTO forms (form, id) VALUES (?, ?)", form_rows)
    return carried


def _settle_merges(con: sqlite3.Connection, slugs: list[str]) -> None:
    """Notes, for each entry created under one of `slugs`, the entry that took that
    slug in a revision, if one has: the entry it is merged into. Two entries created
    under one slug are both kept; only a revision's slug merges. Where several
    entries took it, the lowest id holds, so every machine settles the same way."""
    if slugs:
        con.execute(
            "UPDATE entries SET merged_into = ("
            "  SELECT min(taken.id) FROM slugs AS taken"
            "  WHERE taken.slug = entries.slug AND taken.added = 1 AND taken.id != entries.id"
            ") WHERE slug IN (SELECT value FROM json_each(?))",
            (json.dumps(slugs),),
        )


def _remove(con: sqlite3.Connection, ids: list[tuple]) -> None:
    for table in ("entries", "slugs", "links", "forms"):
        con.executemany(f"DELETE FROM {table} WHERE id = ?", ids)


def plain(name: str) -> str:
    """A name in any case, with its punctuation, hyphens among it, read as spaces."""
    return " ".join("".join(ch if ch.isalnum() else " " for ch in name.lower()).split())


def _texts(values: object) -> list[str]:
    return [value for value in values if isinstance(value, str)] if isinstance(values, list) else []


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
