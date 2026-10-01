"""The read path: finds and returns entries by reading every event file in place.

DuckDB reads the files where they lie, with no index and no second copy, and
every call reads every file afresh, so a machine that has gone quiet can come
back. Reading is generic: entries of every type are found and returned the
same way. It depends on the file format alone, never on the writer.
"""

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path

import duckdb

from .format import FIELDS, events_dir, is_event_file

PAGE = 20
SNIPPET = 160
"""Characters of the body a search hit carries, around the first match."""

_COLUMNS = ", ".join(f"{name}: '{kind}'" for name, kind in {
    "id": "VARCHAR", "type": "VARCHAR", "version": "INTEGER", "recorded_at": "VARCHAR",
    "event_date": "VARCHAR", "description": "VARCHAR", "source": "VARCHAR", "body": "VARCHAR",
    "details": "JSON",
}.items())

# The entries in every file that meet `where`, each id once. A line that is not valid
# JSON, a torn last line among them, comes back empty and is dropped, as is a line
# missing the envelope. A line copied into two files is the same record, so one copy
# is kept. The copies are identical, so any one will do, and filtering before keeping
# one gives the same entries while sparing the many that do not match.
_ENTRIES = """
entries AS (
    SELECT * FROM read_json(
        ?, format = 'newline_delimited', columns = {{{columns}}},
        ignore_errors = true
    )
    WHERE id IS NOT NULL AND type IS NOT NULL AND event_date IS NOT NULL
      AND description IS NOT NULL AND body IS NOT NULL AND {where}
    QUALIFY row_number() OVER (PARTITION BY id) = 1
)
"""


def _entries(where: str) -> str:
    return _ENTRIES.format(columns=_COLUMNS, where=where)


class PatternError(ValueError):
    """A search pattern that is not a valid regular expression."""


@dataclass(frozen=True)
class Hit:
    id: str
    type: str
    event_date: str
    recorded_at: str
    description: str
    snippet: str


@dataclass(frozen=True)
class Page:
    hits: list[Hit]
    total: int
    """How many entries match, across every page."""


class Reader:
    """Reads one event store. Order is by event date, never by file or position."""

    def __init__(self, event_store: Path):
        self.events = events_dir(Path(event_store).resolve())

    def search(
        self,
        pattern: str | None = None,
        *,
        types: list[str] | None = None,
        event_date_from: str | None = None,
        event_date_to: str | None = None,
        recorded_after: str | None = None,
        details: dict[str, str] | None = None,
        newest_first: bool = False,
        limit: int = PAGE,
        offset: int = 0,
    ) -> Page:
        """Finds entries of any type and returns one page of lean hits.

        `pattern` is a regular expression, as grep takes, matched in any case
        against the description and the body. The event dates are inclusive.
        `recorded_after` is a UTC time or date. `details` matches a type's own
        fields exactly. Raises PatternError for a pattern that does not parse.
        """
        if limit < 1 or offset < 0:
            raise ValueError("limit must be at least 1 and offset at least 0")
        where, params = ["true"], []
        if pattern is not None:
            where.append("regexp_matches(description || chr(10) || body, ?, 'i')")
            params.append(pattern)
        if types is not None:
            where.append("list_contains(?::VARCHAR[], type)")
            params.append(list(types))
        if event_date_from is not None:
            where.append("event_date >= ?")
            params.append(_date(event_date_from))
        if event_date_to is not None:
            where.append("event_date <= ?")
            params.append(_date(event_date_to))
        if recorded_after is not None:
            where.append("recorded_at > ?")
            params.append(_utc(recorded_after))
        for name, value in (details or {}).items():
            where.append("json_extract_string(details, ?) = ?")
            params += [_pointer(name), value]
        entries = _entries(" AND ".join(where))
        # The snippet starts a third of its length before the first match in the body.
        if pattern is not None:
            start = f"greatest(1, strpos(body, regexp_extract(body, ?, 0, 'i')) - {SNIPPET // 3})"
            start_params = [pattern]
        else:
            start, start_params = "1", []
        order = "DESC" if newest_first else "ASC"
        sql = f"""
            WITH {entries}, matched AS (
                SELECT id, type, event_date, recorded_at, description, body, {start} AS start
                FROM entries
            ), cut AS (
                SELECT id, type, event_date, recorded_at, description,
                       substr(body, start, {SNIPPET}) AS text, start > 1 AS before,
                       length(body) >= start + {SNIPPET} AS after
                FROM matched
            )
            SELECT *, count(*) OVER () FROM cut
            ORDER BY event_date {order}, id {order}
            LIMIT ? OFFSET ?
        """
        try:
            rows = self._query(sql, [*params, *start_params, limit, offset])
            if rows or not offset:
                total = rows[0][-1] if rows else 0
            else:  # Paged past the end, so no row carried the total.
                [(total,)] = self._query(f"WITH {entries} SELECT count(*) FROM entries", params) or [(0,)]
        except duckdb.InvalidInputException as error:
            raise PatternError(str(error)) from error
        hits = [
            Hit(id, type, event_date, recorded_at, description, _snippet(text, before, after))
            for id, type, event_date, recorded_at, description, text, before, after, _ in rows
        ]
        return Page(hits, total)

    def read(self, ids: list[str]) -> list[dict]:
        """The full records for `ids`, in event-date order. An id not found is left out."""
        rows = self._query(
            f"WITH {_entries('list_contains(?::VARCHAR[], id)')}"
            f" SELECT {', '.join(FIELDS)} FROM entries ORDER BY event_date, id",
            [list(ids)],
        )
        return [_record(row) for row in rows]

    def _query(self, sql: str, params: list) -> list[tuple]:
        """Runs `sql` with the event files as its first parameter, on a fresh connection."""
        paths = sorted(str(p) for p in self.events.glob("*.jsonl") if is_event_file(p.name))
        if not paths:
            return []
        with duckdb.connect() as con:
            return con.execute(sql, [paths, *params]).fetchall()


def _record(row: tuple) -> dict:
    record = dict(zip(FIELDS, row))
    record["details"] = json.loads(record["details"]) if record["details"] else {}
    return record


def _snippet(text: str, before: bool, after: bool) -> str:
    return ("…" if before else "") + " ".join(text.split()) + ("…" if after else "")


def _pointer(name: str) -> str:
    """A JSON pointer to a top-level field of `details`."""
    return "/" + name.replace("~", "~0").replace("/", "~1")


def _date(value: str) -> str:
    try:
        return dt.date.fromisoformat(value).isoformat()
    except (TypeError, ValueError) as error:
        raise ValueError(f"a date must be YYYY-MM-DD: {value!r}") from error


def _utc(value: str) -> str:
    """A time or date as `recorded_at` writes it, so the two compare as text."""
    try:
        at = dt.datetime.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"a time must be ISO 8601: {value!r}") from error
    if at.tzinfo is None:
        at = at.replace(tzinfo=dt.timezone.utc)
    return at.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
