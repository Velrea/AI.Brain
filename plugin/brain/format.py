"""The file format: the shape of a record and the layout of the folders.

Writing and reading both import this module, and neither imports the other.
"""

import datetime as dt
import json
import os
import re
import uuid
from pathlib import Path

EVENTS_DIR = "events"
"""The one flat folder, inside the event store, that holds every event file."""

_FILE_NAME = re.compile(
    r"^h-(?P<id>[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})\.jsonl$"
)

STAMPED = ("id", "recorded_at")
"""Fields the write path sets. A record handed to it must not carry them."""

REQUIRED = ("type", "version", "event_date", "description", "body")
"""Fields every record carries, whatever its type. `source` is optional."""

FIELDS = ("id", "type", "version", "recorded_at", "event_date", "description", "source", "body")
"""The common fields, in the order a record's line holds them. A type may add
fields of its own, which follow them at the top level."""

# Valid inside a JSON string, but a reader that splits lines on them would tear the record.
_LINE_SEPARATORS = {"\u2028": "\\u2028", "\u2029": "\\u2029"}


class RecordError(ValueError):
    """A record that does not have the shape of an entry."""


def events_dir(event_store: Path) -> Path:
    return Path(event_store) / EVENTS_DIR


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


def check(fields: dict) -> dict:
    """Checks the fields a caller hands in for a new record, before stamping.

    Raises RecordError for a missing, blank, or invalid common field, or a
    stamped one. Fields a type adds are checked only for being JSON.
    """
    if not isinstance(fields, dict):
        raise RecordError("a record is an object of fields")
    stamped = [name for name in STAMPED if name in fields]
    if stamped:
        raise RecordError(f"set by the write path, not the caller: {', '.join(stamped)}")
    missing = [name for name in REQUIRED if name not in fields]
    if missing:
        raise RecordError(f"missing required fields: {', '.join(missing)}")

    _text(fields, "type", one_line=True)
    version = fields["version"]
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise RecordError("version must be a whole number from 1")
    _date(fields["event_date"])
    _text(fields, "description", one_line=True)
    _text(fields, "body", one_line=False)
    if "source" in fields:
        _text(fields, "source", one_line=True)

    for name, value in fields.items():
        if not isinstance(name, str) or not name.strip():
            raise RecordError(f"a field's name must be non-empty text: {name!r}")
        try:
            json.dumps(value, allow_nan=False)
        except (TypeError, ValueError) as error:
            raise RecordError(f"{name} is not a JSON value: {error}") from error
    return dict(fields)


def encode(record: dict) -> bytes:
    """One record as one line of UTF-8 JSON, ended by a newline.

    The common fields come first, in their order, then the type's own.
    """
    ordered = {name: record[name] for name in FIELDS if name in record}
    ordered |= {name: value for name, value in record.items() if name not in ordered}
    line = json.dumps(ordered, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    for separator, escaped in _LINE_SEPARATORS.items():
        line = line.replace(separator, escaped)
    try:
        return line.encode("utf-8") + b"\n"
    except UnicodeEncodeError as error:
        raise RecordError("a record must be valid Unicode text") from error


def _text(fields: dict, name: str, *, one_line: bool) -> None:
    value = fields[name]
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
