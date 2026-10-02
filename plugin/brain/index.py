"""The local index: a SQLite database this machine keeps of one event store.

The files are the Brain; the index is a projection of them, kept in the
machine's state folder and never synced. It holds nothing the files do not:
missing, corrupt, or built by another version, it is deleted and rebuilt from
them. Every read catches it up first, taking in only the complete lines each
file has gained since, so a sealed file is read once in its life.

A correction is applied once, when it arrives: the index keeps every record,
and each entry as it stands now, with its revisions applied, or an entity's
statements as one.
"""

import contextlib
import functools
import json
import os
import sqlite3
from collections import defaultdict
from collections.abc import Iterable, Iterator
from pathlib import Path

from .format import events_dir, is_event_file, state_key

VERSION = 1
"""The index's own layout. A change names a new file, so sessions running two
versions of the plugin never rebuild each other's index."""

BUSY_TIMEOUT = 30.0
"""Seconds a session waits for another to finish taking in a file."""

CACHE_KB = 64 * 1024
"""The most memory, in KiB, a connection's page cache holds."""

REVISABLE = ("description", "event_date", "entities")
"""What a revision can replace. A body is never replaced; a revision's body is an amendment."""

_TABLES = ("files", "records", "entries", "subjects", "forms", "words")

# Read in this order from `records`, so a row unpacks as a Record.
_RECORD = "id, entry, type, version, recorded_at, event_date, description, source, body, details, slug"

_SCHEMA = (
    # How many bytes of each file are taken in: every complete line before that point.
    "CREATE TABLE IF NOT EXISTS files (name TEXT PRIMARY KEY, offset INTEGER NOT NULL) WITHOUT ROWID",
    # Every record once, as its line holds it, except an original entry's body, which
    # `entries` keeps. `slug` is set on an entity's statements.
    """CREATE TABLE IF NOT EXISTS records (
        id TEXT PRIMARY KEY, entry TEXT NOT NULL, type TEXT NOT NULL, version INTEGER,
        recorded_at TEXT, event_date TEXT NOT NULL, description TEXT NOT NULL, source TEXT,
        body TEXT, details TEXT NOT NULL, slug TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS records_entry ON records (entry)",
    "CREATE INDEX IF NOT EXISTS records_slug ON records (slug) WHERE slug IS NOT NULL",
    # Every entry as it stands now. `key` is the entry's id, or `entity:<slug>` for an
    # entity, whose `id` is then its newest statement's. `changed_at` is the latest
    # `recorded_at` among the entry's records; `amended` is its amendments as plain text.
    """CREATE TABLE IF NOT EXISTS entries (
        rowid INTEGER PRIMARY KEY, key TEXT NOT NULL UNIQUE, id TEXT NOT NULL,
        type TEXT NOT NULL, version INTEGER, recorded_at TEXT, changed_at TEXT,
        event_date TEXT NOT NULL, description TEXT NOT NULL, source TEXT, body TEXT NOT NULL,
        details TEXT NOT NULL, amendments TEXT NOT NULL, amended TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS entries_order ON entries (event_date, id)",
    # The entities each entry names, and each entity naming itself.
    """CREATE TABLE IF NOT EXISTS subjects (
        slug TEXT NOT NULL, key TEXT NOT NULL, PRIMARY KEY (slug, key)
    ) WITHOUT ROWID""",
    "CREATE INDEX IF NOT EXISTS subjects_key ON subjects (key)",
    # Each entity's slug, name, and aliases, as `resolve` compares them.
    """CREATE TABLE IF NOT EXISTS forms (
        slug TEXT NOT NULL, form TEXT NOT NULL, PRIMARY KEY (slug, form)
    ) WITHOUT ROWID""",
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


class Index:
    """This machine's index of one event store, in its state folder."""

    def __init__(self, event_store: Path, state_dir: Path, *, busy_timeout: float = BUSY_TIMEOUT):
        event_store = Path(event_store).resolve()
        self.events = events_dir(event_store)
        self.state_dir = Path(state_dir)
        self.key = state_key(event_store)
        self.path = self.state_dir / f"{self.key}.index-v{VERSION}.sqlite"
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
        self.state_dir.mkdir(parents=True, exist_ok=True)
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
            try:
                with open(self.events / name, "rb") as file:
                    file.seek(offset)
                    data = file.read()
            except FileNotFoundError:
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
        for path in self.state_dir.glob(f"{self.key}.index-v*.sqlite*"):
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
    details = details if isinstance(details, dict) else {}
    slug = details.get("slug")
    is_statement = type == "entity" and entry == id and isinstance(slug, str) and slug
    return (
        id, entry, type,
        version if isinstance(version, int) and not isinstance(version, bool) else None,
        recorded_at if isinstance(recorded_at, str) else None,
        event_date, description,
        source if isinstance(source, str) else None,
        body,
        json.dumps(details, ensure_ascii=False, separators=(",", ":")),
        slug if is_statement else None,
    )


def _add(con: sqlite3.Connection, records: list[tuple]) -> None:
    """Adds records, each id once, and settles every entry they touch."""
    rows, bodies, entries, slugs = [], {}, set(), set()
    for record in records:
        id, entry, *_, slug = record
        if slug is not None:
            slugs.add(slug)
        else:
            entries.add(entry)  # An original's own id, or the entry a revision revises.
            if entry == id:
                # Its body goes to `entries` alone, so the index holds it once.
                bodies.setdefault(id, record[8])
                record = (*record[:8], None, *record[9:])
        rows.append(record)
    con.executemany(f"INSERT OR IGNORE INTO records ({_RECORD}) VALUES ({', '.join('?' * 11)})", rows)
    _settle_entries(con, sorted(entries), bodies)
    _settle_entities(con, sorted(slugs))


def _settle_entries(con: sqlite3.Connection, keys: list[str], bodies: dict[str, str]) -> None:
    """Rewrites each entry as it stands now: its original with its revisions applied.

    A revision is a journal record whose `entry` names an original journal entry.
    For each field, the newest revision setting it wins, by id, so two machines
    revising different fields before they sync both hold. A revision whose
    original has not arrived waits in `records` until it does. `bodies` are the
    bodies of originals just taken in; an earlier one's is in its entry's row.
    """
    if not keys:
        return
    wanted = json.dumps(keys)
    bodies = dict(con.execute(
        "SELECT key, body FROM entries WHERE key IN (SELECT value FROM json_each(?))", (wanted,),
    )) | bodies
    originals = {
        row[0]: row for row in con.execute(
            f"SELECT {_RECORD} FROM records"
            " WHERE id IN (SELECT value FROM json_each(?)) AND entry = id AND slug IS NULL",
            (wanted,),
        )
    }
    revisions = defaultdict(list)
    for row in con.execute(
        f"SELECT {_RECORD} FROM records"
        " WHERE entry IN (SELECT value FROM json_each(?)) AND id != entry AND type = 'journal'"
        " ORDER BY id",
        (wanted,),
    ):
        revisions[row[1]].append(row)
    _remove(con, [(key,) for key in keys])
    rows, subjects = [], []
    for key in keys:
        original = originals.get(key)
        if original is None:
            continue
        id, _, type, version, recorded_at, event_date, description, source, _, details, _ = original
        body = bodies[key]
        details = json.loads(details)
        amendments, changed_at = [], recorded_at
        for revision in revisions[key] if type == "journal" else ():
            r_id, _, _, _, r_recorded_at, r_event_date, r_description, _, r_body, r_details, _ = revision
            r_details = json.loads(r_details)
            sets = r_details.get("revises")
            sets = set(sets) & set(REVISABLE) if isinstance(sets, list) else set()
            if "description" in sets:
                description = r_description
            if "event_date" in sets:
                event_date = r_event_date
            if "entities" in sets:
                details["entities"] = r_details.get("entities") or []
            if r_body.strip():
                amendments.append({"id": r_id, "recorded_at": r_recorded_at, "body": r_body})
            changed_at = max(filter(None, (changed_at, r_recorded_at)), default=None)
        if details.get("entities") == []:
            del details["entities"]
        rows.append((
            key, id, type, version, recorded_at, changed_at, event_date, description, source, body,
            _json(details), _json(amendments), "\n\n".join(a["body"] for a in amendments),
        ))
        subjects += [(slug, key) for slug in _texts(details.get("entities"))]
    _insert(con, rows, subjects)


def _settle_entities(con: sqlite3.Connection, slugs: list[str]) -> None:
    """Rewrites each entity as its statements hold it now: its name, kind, and body
    the newest statement's, by event date and then id, and its aliases every
    statement's, so two machines adding aliases before they sync lose neither."""
    if not slugs:
        return
    statements = defaultdict(list)
    for row in con.execute(
        f"SELECT {_RECORD} FROM records WHERE slug IN (SELECT value FROM json_each(?))"
        " ORDER BY event_date DESC, id DESC",
        (json.dumps(slugs),),
    ):
        statements[row[-1]].append(row)
    keys = [f"entity:{slug}" for slug in slugs]
    _remove(con, [(key,) for key in keys])
    con.executemany("DELETE FROM forms WHERE slug = ?", [(slug,) for slug in slugs])
    rows, subjects, forms = [], [], []
    for slug, key in zip(slugs, keys):
        newest = statements[slug][0]
        id, _, type, version, recorded_at, event_date, name, source, body, details, _ = newest
        details = json.loads(details)
        aliases = sorted({
            alias for statement in statements[slug]
            for alias in _texts(json.loads(statement[9]).get("aliases"))
        })
        details["aliases"] = aliases
        changed_at = max(filter(None, (statement[4] for statement in statements[slug])), default=None)
        rows.append((
            key, id, type, version, recorded_at, changed_at, event_date, name, source, body,
            _json(details), "[]", "",
        ))
        subjects.append((slug, key))
        forms += {(slug, form) for form in map(plain, [slug, name, *aliases]) if form}
    _insert(con, rows, subjects)
    con.executemany("INSERT OR IGNORE INTO forms (slug, form) VALUES (?, ?)", forms)


def _remove(con: sqlite3.Connection, keys: list[tuple]) -> None:
    con.executemany("DELETE FROM entries WHERE key = ?", keys)
    con.executemany("DELETE FROM subjects WHERE key = ?", keys)


def _insert(con: sqlite3.Connection, rows: list[tuple], subjects: list[tuple]) -> None:
    con.executemany(
        "INSERT INTO entries (key, id, type, version, recorded_at, changed_at, event_date,"
        " description, source, body, details, amendments, amended)"
        f" VALUES ({', '.join('?' * 13)})",
        rows,
    )
    con.executemany("INSERT OR IGNORE INTO subjects (slug, key) VALUES (?, ?)", subjects)


def plain(name: str) -> str:
    """A name in any case, with its punctuation, hyphens among it, read as spaces."""
    return " ".join("".join(ch if ch.isalnum() else " " for ch in name.lower()).split())


def _texts(values: object) -> Iterable[str]:
    return [value for value in values if isinstance(value, str)] if isinstance(values, list) else []


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
