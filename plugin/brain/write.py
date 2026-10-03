"""The write path: the one write for every type, which creates an entry or
revises one, checks it, stamps it, and appends it as one line.

What a type means is its skill's: the type and its version are the caller's
to give, and its own fields go in `details`. What every entry obeys is checked
here, against what the index holds: a new entry's slug is one no entry
carries, each link names a slug some entry carries, and a revision names an
entry of its own type. Only this module writes the event files. Each machine
appends only to files it created, and sessions on one machine take turns
through a lock in the machine's plugin data folder, outside the synced folders.
"""

import datetime as dt
import json
import os
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from .format import (
    REVISABLE,
    RecordError,
    brain_key,
    check_entry,
    check_slug,
    encode,
    events_dir,
    file_created_at,
    is_event_file,
    new_file_name,
    uuid7,
    uuid7_ms,
)
from .lock import FileLock
from .read import Reader

ROLL_LINES = 10_000
ROLL_AGE = dt.timedelta(days=7)

LOCK_TIMEOUT = 30.0
"""Seconds a session waits for the lock. It is held for milliseconds."""

APPEND_RETRY = 10.0
"""Seconds an append blocked by another process keeps retrying."""


class AppendBlocked(OSError):
    """The event file stayed blocked by another process past the retries."""


class SlugTaken(RecordError):
    """A new entry's slug is one an entry already carries."""

    def __init__(self, slug: str, holders: list[tuple[str, str]]):
        held = "; ".join(f"{id} ({description})" for id, description in holders)
        super().__init__(
            f"the slug {slug!r} is already recorded, by {held}: revise that entry with its id as entry,"
            f" or give this one a slug of its own"
        )
        self.slug = slug


class UnknownLinks(RecordError):
    """An entry linked to slugs no entry carries."""

    def __init__(self, slugs: list[str]):
        super().__init__(f"no entry carries {', '.join(slugs)}: search for the slug, or create its entry first")
        self.slugs = slugs


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Writer:
    """Writes entries to one Brain folder from this machine.

    `data_dir` is this machine's own folder, never a synced one: the
    plugin's data folder. It holds the lock file, the name of the file this
    machine appends to, and the index the checks read.
    """

    def __init__(
        self,
        brain_dir: Path,
        data_dir: Path,
        *,
        lock_timeout: float = LOCK_TIMEOUT,
        append_retry: float = APPEND_RETRY,
        clock: Callable[[], dt.datetime] = utc_now,
    ):
        self.brain_dir = Path(brain_dir).resolve()
        self.events = events_dir(self.brain_dir)
        self.append_retry = append_retry
        self.clock = clock
        key = brain_key(self.brain_dir)
        self._state_path = Path(data_dir) / f"{key}.json"
        self._lock = FileLock(Path(data_dir) / f"{key}.lock", lock_timeout)
        self.reader = Reader(self.brain_dir, data_dir)

    def write(
        self,
        *,
        type: str,
        version: int,
        entry: str | None = None,
        slug: str | None = None,
        event_date: str | None = None,
        description: str | None = None,
        body: str | None = None,
        links: Sequence[str] | None = None,
        aliases: Sequence[str] = (),
        details: Mapping | None = None,
        source: str | None = None,
    ) -> str:
        """Creates an entry, or revises the one `entry` names, and returns the record's id.

        To create, give `slug`, `event_date`, `description`, and `body`; a slug
        an entry already carries raises SlugTaken. To revise, give `entry`, the
        id of an entry of the same type, and what changes: `description`,
        `event_date`, and `links` each replace the entry's; each field of
        `details` replaces the entry's field of that name, a None removing it;
        `slug` and `aliases` add to the entry's names, and a slug another entry
        was created under merges that entry into this one; `body` is an
        amendment kept under the entry's body, which is never replaced. A link
        no entry carries raises UnknownLinks, and nothing is written. Slugs
        are never removed, so a link found here still resolves when written.
        Raises RecordError for a blank or invalid field, LockTimeout when
        another session holds the lock too long, and AppendBlocked when the
        file stays blocked past the retries.
        """
        aliases = _lines("aliases", aliases)
        if links is not None:
            links = self._linked(links)
        if details is not None and not isinstance(details, Mapping):
            raise RecordError("details must be an object of fields")
        details = dict(details or {})
        if entry is None:
            check_slug("slug", slug)
            if holders := self.reader.holders([slug]).get(slug):
                raise SlugTaken(slug, holders)
            return self._append(
                type=type, version=version, event_date=event_date, description=description, body=body,
                source=source, slugs=[slug], aliases=aliases, links=links or [], details=details,
            )
        if slug is not None:
            check_slug("slug", slug)
        given = {"description": description, "event_date": event_date, "links": links}
        revises = [name for name in REVISABLE if given[name] is not None]
        if not (revises or slug or aliases or details or body is not None):
            raise RecordError("a revision must change the description, event date, links, slugs, aliases, or"
                              " details, or add an amendment")
        if body is not None and (not isinstance(body, str) or not body.strip()):
            raise RecordError("an amendment must be non-empty text")
        current = next(iter(self.reader.read([entry])), None)
        if current is None:
            raise RecordError(f"no entry has the id {entry!r}")
        if current["type"] != type:
            raise RecordError(f"entry {current['id']} is a {current['type']}, not a {type}")
        return self._append(
            entry=current["id"],
            type=type,
            version=version,
            # Whole on its own: what it does not revise is the entry's as it stood.
            event_date=current["event_date"] if event_date is None else event_date,
            description=current["description"] if description is None else description,
            body=body or "",
            source=source,
            slugs=[slug] if slug else [],
            aliases=aliases,
            links=current["links"] if links is None else links,
            revises=revises,
            details=details,
        )

    def _linked(self, links: object) -> list[str]:
        """The links, each checked as a slug some entry carries."""
        if isinstance(links, str) or not isinstance(links, Sequence):
            raise RecordError("links must be a list")
        links = list(dict.fromkeys(links))
        for link in links:
            check_slug("links", link)
        missing = sorted(set(links) - set(self.reader.holders(links))) if links else []
        if missing:
            raise UnknownLinks(missing)
        return links

    def _append(
        self,
        *,
        entry: str | None = None,
        type: str,
        version: int,
        event_date: str,
        description: str,
        body: str,
        source: str | None = None,
        slugs: list[str] | None = None,
        aliases: list[str] | None = None,
        links: list[str] | None = None,
        revises: list[str] | None = None,
        details: dict | None = None,
    ) -> str:
        """Checks a record's shape, stamps it, and appends it, returning its id.

        `id` and `recorded_at` are stamped here, and `entry`, the entry the
        record belongs to, is its own id unless it is given: a revision names
        the entry it revises, and its body, an amendment, may be empty.
        """
        lists = {
            "slugs": slugs or [], "aliases": aliases or [], "links": links or [], "revises": revises or [],
        }
        details = {} if details is None else details
        check_entry(
            entry=entry, type=type, version=version, event_date=event_date,
            description=description, body=body, source=source, details=details, **lists,
        )
        record = {
            "type": type, "version": version, "event_date": event_date,
            "description": description, "body": body, **lists, "details": details,
        }
        if source is not None:
            record["source"] = source
        with self._lock:
            now = self.clock()
            # Later than every id this machine wrote here: what orders by id must not
            # turn on chance within a millisecond.
            stamp = uuid7(now, after=self._last_ms())
            id = str(stamp)
            record |= {"id": id, "entry": entry or id, "recorded_at": _utc_text(now)}
            line = encode(record)
            self._retrying(lambda: self._append_line(line, now, uuid7_ms(stamp)))
        return record["id"]

    def _retrying(self, attempt: Callable[[], None]) -> None:
        deadline = time.monotonic() + self.append_retry
        delay = 0.05
        while True:
            try:
                return attempt()
            except PermissionError as error:
                if time.monotonic() >= deadline:
                    raise AppendBlocked(f"the event file stayed blocked: {error}") from error
                time.sleep(delay)
                delay = min(delay * 2, 1.0)

    def _append_line(self, line: bytes, now: dt.datetime, last_ms: int) -> None:
        path, lines = self._current_file(now)
        if path is None:
            self.events.mkdir(parents=True, exist_ok=True)
            path, lines = self.events / new_file_name(now), 0
        _append(path, line)
        lines += 1
        # Leave the store ready for the next writer: a file that is due is rolled now.
        current = None if self._due(path, lines, now) else {"file": path.name, "lines": lines}
        self._save_state(current, last_ms)

    def _current_file(self, now: dt.datetime) -> tuple[Path | None, int]:
        """The file this machine appends to and its line count, or None to start one."""
        state = self._load_state()
        if state is None:
            return None, 0
        path = self.events / state["file"]
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            return None, 0
        lines = state["lines"]
        if size and not _ends_with_newline(path):
            # A crash mid-append left a torn last line. End it; never truncate.
            _append(path, b"\n")
            lines += 1
        if self._due(path, lines, now):
            return None, 0
        return path, lines

    def _due(self, path: Path, lines: int, now: dt.datetime) -> bool:
        return lines >= ROLL_LINES or now - file_created_at(path.name) >= ROLL_AGE

    def _load_state(self) -> dict | None:
        """This machine's current file, or None when there is none it can trust."""
        state = self._read_state()
        if not is_event_file(state.get("file") or "") or not isinstance(state.get("lines"), int):
            return None
        return state

    def _last_ms(self) -> int:
        """The time of the last id this machine wrote here, or -1."""
        last = self._read_state().get("last_ms")
        return last if isinstance(last, int) else -1

    def _read_state(self) -> dict:
        try:
            state = json.loads(self._state_path.read_text("utf-8"))
        except (FileNotFoundError, ValueError):
            return {}
        if not isinstance(state, dict) or state.get("brain_dir") != str(self.brain_dir):
            return {}
        return state

    def _save_state(self, current: dict | None, last_ms: int) -> None:
        state = {"brain_dir": str(self.brain_dir), "last_ms": last_ms, **(current or {})}
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self._state_path.with_suffix(".tmp")
        temp.write_text(json.dumps(state), "utf-8")
        os.replace(temp, self._state_path)


def _append(path: Path, data: bytes) -> None:
    """Appends `data` in one unbuffered write, and returns once it is on disk."""
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0)
    fd = os.open(path, flags, 0o644)
    try:
        view = memoryview(data)
        while view:  # One write in practice; the loop only guards a short write.
            view = view[os.write(fd, view):]
        os.fsync(fd)
    finally:
        os.close(fd)


def _utc_text(at: dt.datetime) -> str:
    return at.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _lines(name: str, values: object) -> list[str]:
    """Each value checked as one line of text, once each, in the order given."""
    if isinstance(values, str) or not isinstance(values, Sequence):
        raise RecordError(f"{name} must be a list")
    for value in values:
        if not isinstance(value, str) or not value.strip() or value.splitlines() != [value]:
            raise RecordError(f"{name} must each be one line of non-empty text")
    return list(dict.fromkeys(values))


def _ends_with_newline(path: Path) -> bool:
    with open(path, "rb") as file:
        file.seek(-1, os.SEEK_END)
        return file.read(1) == b"\n"
