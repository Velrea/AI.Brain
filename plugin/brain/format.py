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
"""The one flat folder, inside the Brain folder, that holds every event file."""

_UUID7 = r"[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
_FILE_NAME = re.compile(rf"^h-(?P<id>{_UUID7})\.jsonl$")

FIELDS = (
    "id", "entry", "type", "version", "recorded_at", "event_date", "description", "source", "body",
    "slugs", "aliases", "links", "revises", "details",
)
"""The envelope every record carries, in the order its line holds them. `entry` is
the entry the record belongs to: its own id on an original, the original's on a
revision. `slugs` are the entry's names, one on an original and any added on a
revision; `aliases` are other names it goes by; `links` are the slugs of the
entries it is about; `revises` names what a revision replaces, and is empty on
an original. `source` is the only optional field. What a type adds goes in
`details`, never beside it."""

REVISABLE = ("description", "event_date", "links")
"""What a revision can replace. A body is never replaced; a revision's body is an amendment."""

SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
"""A slug: lowercase letters and digits, in words joined by hyphens."""

# Valid inside a JSON string, but a reader that splits lines on them would tear the record.
_LINE_SEPARATORS = {"\u2028": "\\u2028", "\u2029": "\\u2029"}


class RecordError(ValueError):
    """A record that does not have the shape of an entry."""


def events_dir(brain_dir: Path) -> Path:
    return Path(brain_dir) / EVENTS_DIR


def brain_key(brain_dir: Path) -> str:
    """Names this machine's files for one Brain folder, so two Brains on one
    machine never share a lock, a current file, or an index."""
    path = os.path.normcase(str(Path(brain_dir).resolve()))
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


def uuid7(at: dt.datetime, *, after: int = -1) -> uuid.UUID:
    """A UUIDv7 (RFC 9562) whose time is `at`, to the millisecond, or the
    millisecond past `after` when `at` is no later, so a writer's ids order
    as it wrote them even within one millisecond."""
    ms = max(int(at.timestamp() * 1000), after + 1) & ((1 << 48) - 1)
    rand = int.from_bytes(os.urandom(10), "big")
    rand_a = rand >> 68 & 0xFFF
    rand_b = rand & ((1 << 62) - 1)
    return uuid.UUID(int=ms << 80 | 0x7 << 76 | rand_a << 64 | 0b10 << 62 | rand_b)


def uuid7_ms(value: uuid.UUID) -> int:
    """The time of a UUIDv7, in milliseconds since the epoch."""
    return value.int >> 80


def uuid7_time(value: uuid.UUID) -> dt.datetime:
    return dt.datetime.fromtimestamp(uuid7_ms(value) / 1000, dt.timezone.utc)


def check_entry(
    *,
    entry: str | None = None,
    type: str,
    version: int,
    event_date: str,
    description: str,
    body: str,
    source: str | None,
    slugs: list,
    aliases: list,
    links: list,
    revises: list,
    details: dict,
) -> None:
    """Raises RecordError for a blank or invalid field of the envelope.

    `entry` is given only for a revision, whose body is an amendment and may
    be empty when it changes only metadata. An original carries one slug and
    revises nothing.
    """
    if entry is not None and (not isinstance(entry, str) or re.fullmatch(_UUID7, entry) is None):
        raise RecordError(f"entry must be the id of an entry: {entry!r}")
    check_slug("type", type)
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise RecordError("version must be a whole number from 1")
    _date(event_date)
    _text("description", description, one_line=True)
    if entry is None or body != "":
        _text("body", body, one_line=False)
    if source is not None:
        _text("source", source, one_line=True)
    for name, values in (("slugs", slugs), ("links", links)):
        for value in _list(name, values):
            check_slug(name, value)
    for alias in _list("aliases", aliases):
        _text("aliases", alias, one_line=True)
    if any(name not in REVISABLE for name in _list("revises", revises)):
        raise RecordError(f"revises names only {', '.join(REVISABLE)}")
    if entry is None and (len(slugs) != 1 or revises):
        raise RecordError("an original carries one slug and revises nothing")
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


def check_slug(name: str, value: object) -> None:
    if not isinstance(value, str) or SLUG.fullmatch(value) is None:
        raise RecordError(f"{name} must be a slug, lowercase letters and digits in words joined by hyphens: {value!r}")


def _list(name: str, values: object) -> list:
    if not isinstance(values, list):
        raise RecordError(f"{name} must be a list")
    return values


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
