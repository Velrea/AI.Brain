"""The write path: validates a record, stamps it, and appends it as one line.

Only this module writes the event store. Each machine appends only to files
it created, and sessions on one machine take turns through a lock in the
machine's state folder, outside the synced folders.
"""

import datetime as dt
import hashlib
import json
import os
import time
from collections.abc import Callable
from pathlib import Path

from .format import check, encode, events_dir, file_created_at, is_event_file, new_file_name, uuid7
from .lock import FileLock

ROLL_LINES = 10_000
ROLL_AGE = dt.timedelta(days=7)

LOCK_TIMEOUT = 30.0
"""Seconds a session waits for the lock. It is held for milliseconds."""

APPEND_RETRY = 10.0
"""Seconds an append blocked by another process, such as the sync service, keeps retrying."""


class AppendBlocked(OSError):
    """The event file stayed blocked by another process past the retries."""


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Writer:
    """Appends records to one event store from this machine.

    `state_dir` is this machine's own folder, never a synced one: the
    plugin's data folder. It holds the lock file and the name of the file
    this machine appends to.
    """

    def __init__(
        self,
        event_store: Path,
        state_dir: Path,
        *,
        lock_timeout: float = LOCK_TIMEOUT,
        append_retry: float = APPEND_RETRY,
        clock: Callable[[], dt.datetime] = utc_now,
    ):
        self.event_store = Path(event_store).resolve()
        self.events = events_dir(self.event_store)
        self.append_retry = append_retry
        self.clock = clock
        # Named for the event store's path, so two Brains never share a lock or a current file.
        key = hashlib.sha256(os.path.normcase(str(self.event_store)).encode()).hexdigest()[:16]
        self._state_path = Path(state_dir) / f"{key}.json"
        self._lock = FileLock(Path(state_dir) / f"{key}.lock", lock_timeout)

    def append(self, fields: dict) -> str:
        """Records an entry and returns its id.

        `fields` carries every field but `id` and `recorded_at`, which are
        stamped here. Raises RecordError for a record of the wrong shape,
        LockTimeout when another session holds the lock too long, and
        AppendBlocked when the file stays blocked past the retries.
        """
        fields = check(fields)
        with self._lock:
            now = self.clock()
            record = {"id": str(uuid7(now)), "recorded_at": _utc_text(now)} | fields
            line = encode(record)
            self._retrying(lambda: self._append_line(line, now))
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

    def _append_line(self, line: bytes, now: dt.datetime) -> None:
        path, lines = self._current_file(now)
        if path is None:
            self.events.mkdir(parents=True, exist_ok=True)
            path, lines = self.events / new_file_name(now), 0
        _append(path, line)
        lines += 1
        # Leave the store ready for the next writer: a file that is due is rolled now.
        self._save_state(None if self._due(path, lines, now) else {"file": path.name, "lines": lines})

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
        try:
            state = json.loads(self._state_path.read_text("utf-8"))
        except (FileNotFoundError, ValueError):
            return None
        if (
            not isinstance(state, dict)
            or state.get("event_store") != str(self.event_store)
            or not is_event_file(state.get("file") or "")
            or not isinstance(state.get("lines"), int)
        ):
            return None
        return state

    def _save_state(self, current: dict | None) -> None:
        state = {"event_store": str(self.event_store), **(current or {})}
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self._state_path.with_suffix(".tmp")
        temp.write_text(json.dumps(state), "utf-8")
        os.replace(temp, self._state_path)


def _append(path: Path, data: bytes) -> None:
    with open(path, "ab") as file:
        file.write(data)
        file.flush()
        os.fsync(file.fileno())


def _utc_text(at: dt.datetime) -> str:
    return at.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ends_with_newline(path: Path) -> bool:
    with open(path, "rb") as file:
        file.seek(-1, os.SEEK_END)
        return file.read(1) == b"\n"
