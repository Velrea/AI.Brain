"""The file format: the shape of a record and the layout of the folders.

Writing and reading both import this module, and neither imports the other.
"""

import datetime as dt
import hashlib
import json
import os
import re
import uuid
from pathlib import Path

EVENTS_DIR = "events"
"""The one flat folder, inside the event store, that holds every event file."""

_UUID7 = r"[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
_FILE_NAME = re.compile(rf"^h-(?P<id>{_UUID7})\.jsonl$")

FIELDS = (
    "id", "entry", "type", "version", "recorded_at", "event_date", "description", "source", "body",
    "details",
)
"""The envelope every record carries, in the order its line holds them. `entry` is
the entry the record belongs to: its own id on an original, the original's on a
revision. `source` is the only optional field. What a type adds goes in `details`,
never beside it."""

# Valid inside a JSON string, but a reader that splits lines on them would tear the record.
_LINE_SEPARATORS = {"\u2028": "\\u2028", "\u2029": "\\u2029"}


class RecordError(ValueError):
    """A record that does not have the shape of an entry."""


def events_dir(event_store: Path) -> Path:
    return Path(event_store) / EVENTS_DIR


def state_key(event_store: Path) -> str:
    """Names this machine's state for one event store, so two Brains on one
    machine never share a lock, a current file, or an index."""
    path = os.path.normcase(str(Path(event_store).resolve()))
    return hashlib.sha256(path.encode()).hexdigest()[:16]


def new_file_name(at: dt.datetime) -> str:
    """Names a new event file for a machine that starts one at `at`."""
    return f"h-{uuid7(at)}.jsonl"


def is_event_file(name: str) -> bool:
    return _FILE_NAME.match(name) is not None


def file_created_at(name: str) -> dt.datetime:
    """When the file was started, by the time in its name."""
    match = _FILE_NAME.match(name)
    if match is None:
        raise ValueError(f"not an event file name: {name!r}")
    return uuid7_time(uuid.UUID(match["id"]))


def uuid7(at: dt.datetime) -> uuid.UUID:
    """A UUIDv7 (RFC 9562) whose time is `at`, to the millisecond."""
    ms = int(at.timestamp() * 1000) & ((1 << 48) - 1)
    rand = int.from_bytes(os.urandom(10), "big")
    rand_a = rand >> 68 & 0xFFF
    rand_b = rand & ((1 << 62) - 1)
    return uuid.UUID(int=ms << 80 | 0x7 << 76 | rand_a << 64 | 0b10 << 62 | rand_b)


def uuid7_time(value: uuid.UUID) -> dt.datetime:
    return dt.datetime.fromtimestamp((value.int >> 80) / 1000, dt.timezone.utc)


def check_entry(
    *,
    entry: str | None = None,
    type: str,
    version: int,
    event_date: str,
    description: str,
    body: str,
    source: str | None,
    details: dict,
) -> None:
    """Raises RecordError for a blank or invalid field of the envelope.

    `entry` is given only for a revision, whose body is an amendment and may
    be empty when it changes only metadata.
    """
    if entry is not None and (not isinstance(entry, str) or re.fullmatch(_UUID7, entry) is None):
        raise RecordError(f"entry must be the id of an entry: {entry!r}")
    _text("type", type, one_line=True)
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise RecordError("version must be a whole number from 1")
    _date(event_date)
    _text("description", description, one_line=True)
    if entry is None or body != "":
        _text("body", body, one_line=False)
    if source is not None:
        _text("source", source, one_line=True)
    if not isinstance(details, dict):
        raise RecordError("details must be an object of fields")
    for name, value in details.items():
        if not isinstance(name, str) or not name.strip():
            raise RecordError(f"a detail's name must be non-empty text: {name!r}")
        try:
            json.dumps(value, allow_nan=False)
        except (TypeError, ValueError) as error:
            raise RecordError(f"detail {name} is not a JSON value: {error}") from error


def encode(record: dict) -> bytes:
    """One record as one line of UTF-8 JSON, ended by a newline."""
    ordered = {name: record[name] for name in FIELDS if name in record}
    line = json.dumps(ordered, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    for separator, escaped in _LINE_SEPARATORS.items():
        line = line.replace(separator, escaped)
    try:
        return line.encode("utf-8") + b"\n"
    except UnicodeEncodeError as error:
        raise RecordError("a record must be valid Unicode text") from error


def _text(name: str, value: object, *, one_line: bool) -> None:
    if not isinstance(value, str) or not value.strip():
        raise RecordError(f"{name} must be non-empty text")
    if one_line and value.splitlines() != [value]:
        raise RecordError(f"{name} must be one line")


def _date(value: object) -> None:
    if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        raise RecordError("event_date must be a date, YYYY-MM-DD")
    try:
        dt.date.fromisoformat(value)
    except ValueError as error:
        raise RecordError(f"event_date is not a real date: {value}") from error
