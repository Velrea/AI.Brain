"""The read path: finds and returns entries from this machine's local index.

Every call catches the index up with the files first, so a machine that has
gone quiet can come back and its records are simply there. Reading is generic:
entries of every type are found and returned the same way, and only resolving
names to entities knows a type. It depends on the file format and the index,
never on the writer.
"""

import datetime as dt
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .format import FIELDS
from .index import Index, plain

CEILING = 100
"""The most hits a search returns. One that finds more returns none, so a
caller never mistakes part of a result for the whole of it."""
RANGES = 12
"""The most event-date ranges a refusal suggests; past that it counts by year."""
SNIPPET = 160
"""Characters of the body a hit carries when no pattern picks where to cut it."""
SNIPPET_WORDS = 25
"""Words a hit's snippet carries around the best match of a pattern."""
MATCHES = 5
"""Entities resolving returns for each name, at most."""
LIKELY = 0.8
"""The least score, from 0 to 1, an entity needs to be a likely match for a name."""

# A pattern's terms: a "quoted phrase" or a bare word, either one excluded by a
# leading hyphen or ending in * to match as a prefix.
_TERM = re.compile(r'(-?)"([^"]*)"?(\*?)|(\S+)')
# Marks where FTS5 found a match in a snippet, to tell which column matched.
_START, _END = "\x02", "\x03"
_SHA256 = re.compile(r"[0-9a-f]{64}")


class PatternError(ValueError):
    """A search pattern with nothing to look for."""


class TooManyHits(ValueError):
    """A search that found more entries than it returns, so returned none.

    `ranges` split the entries by event date, each a (from, to, count), every
    one within the ceiling where dates alone can make it so.
    """

    def __init__(self, total: int, ranges: list[tuple[str, str, int]]):
        self.total = total
        self.ranges = ranges
        if len(ranges) <= RANGES:
            spans = ", ".join(
                f"{start} ({count})" if start == end else f"{start} to {end} ({count})"
                for start, end, count in ranges
            )
            by_date = f"search these event-date ranges, each {CEILING} or fewer: {spans}"
        else:
            years = {}
            for start, _, count in ranges:
                years[start[:4]] = years.get(start[:4], 0) + count
            spans = ", ".join(f"{year} ({count})" for year, count in years.items())
            by_date = f"search by event date; by year: {spans}"
        super().__init__(
            f"{total} entries match, more than the {CEILING} a search returns. Refine it: add"
            f" words, entities, types, or details to narrow it, split it into more targeted"
            f" searches, or {by_date}."
        )


@dataclass(frozen=True)
class Hit:
    id: str
    type: str
    event_date: str
    recorded_at: str
    description: str
    snippet: str


@dataclass(frozen=True)
class Entity:
    id: str
    """The id of the statement that holds, to read its body."""
    slug: str
    name: str
    kind: str
    aliases: list[str]


class Reader:
    """Reads one Brain folder through this machine's index of it, kept in
    `data_dir`. Order is by event date, never by file or position."""

    def __init__(self, brain_dir: Path, data_dir: Path):
        self.index = Index(brain_dir, data_dir)

    def search(
        self,
        pattern: str | None = None,
        *,
        types: list[str] | None = None,
        event_date_from: str | None = None,
        event_date_to: str | None = None,
        recorded_after: str | None = None,
        details: dict[str, str] | None = None,
        entities: list[str] | None = None,
        documents: list[str] | None = None,
        newest_first: bool = False,
    ) -> list[Hit]:
        """Finds entries of any type and returns every one as a lean hit.

        `pattern` is words to find, in any case, in the description, the body,
        or an amendment: every word must appear, in any form of it, so `drop`
        finds "drops". A "quoted phrase" must appear as written, a word or
        phrase ending in * matches as a prefix, one starting with - must not
        appear, and OR between terms finds either side. `entities` are slugs:
        an entry that names any of them is a hit, and so is the entity itself.
        Given both, an entry is a hit when either finds it, so an entry whose
        entities were missed when it was written is still found by its words.
        The event dates are inclusive. `recorded_after` is a UTC time or date,
        and finds entries recorded or revised after it. `details` matches a
        type's own fields exactly. `documents` are sha256 hashes: only an
        entry naming a filed document with one of them is a hit. Raises PatternError for a pattern with
        nothing to look for, and TooManyHits, with how to refine it, when more
        entries match than the ceiling.
        """
        where, params = ["true"], []
        found, found_params = [], []
        match = _match(pattern) if pattern is not None else None
        if match is not None:
            found.append("rowid IN (SELECT rowid FROM words WHERE words MATCH ?)")
            found_params.append(match)
        if entities is not None:
            found.append("key IN (SELECT key FROM subjects WHERE slug IN (SELECT value FROM json_each(?)))")
            found_params.append(json.dumps(list(entities)))
        if found:
            where.append(f"({' OR '.join(found)})")
            params += found_params
        if documents is not None:
            for digest in documents:
                if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
                    raise ValueError(f"a document's sha256 is 64 lowercase hex characters: {digest!r}")
            where.append(
                "EXISTS (SELECT 1 FROM json_each(details, '$.documents') AS document"
                " WHERE json_extract(document.value, '$.sha256') IN (SELECT value FROM json_each(?)))"
            )
            params.append(json.dumps(list(documents)))
        if types is not None:
            where.append("type IN (SELECT value FROM json_each(?))")
            params.append(json.dumps(list(types)))
        if event_date_from is not None:
            where.append("event_date >= ?")
            params.append(_date(event_date_from))
        if event_date_to is not None:
            where.append("event_date <= ?")
            params.append(_date(event_date_to))
        if recorded_after is not None:
            where.append("changed_at > ?")
            params.append(_utc(recorded_after))
        for name, value in (details or {}).items():
            path = _path(name)
            # As text, the way JSON writes it, so a number or a flag matches too.
            where.append(
                "CASE json_type(details, ?) WHEN 'true' THEN 'true' WHEN 'false' THEN 'false'"
                " ELSE CAST(json_extract(details, ?) AS TEXT) END = ?"
            )
            params += [path, path, str(value)]
        conditions = " AND ".join(where)
        order = "DESC" if newest_first else "ASC"
        with self.index.connect() as con:
            rows = con.execute(
                f"SELECT rowid, id, type, event_date, recorded_at, description"
                f" FROM entries WHERE {conditions}"
                f" ORDER BY event_date {order}, id {order} LIMIT ?",
                [*params, CEILING + 1],
            ).fetchall()
            if len(rows) > CEILING:
                days = con.execute(
                    f"SELECT event_date, count(*) FROM entries WHERE {conditions}"
                    " GROUP BY event_date ORDER BY event_date",
                    params,
                ).fetchall()
                raise TooManyHits(sum(count for _, count in days), _ranges(days))
            snippets = _snippets(con, [row[0] for row in rows], match)
        return [
            Hit(id, type, event_date, recorded_at, description, snippets[rowid])
            for rowid, id, type, event_date, recorded_at, description in rows
        ]

    def resolve(self, names: list[str], *, limit: int = MATCHES) -> dict[str, list[Entity]]:
        """The likely matching entities for each name, best first.

        A name matches an entity's slug, name, or an alias the same in any
        case and punctuation, held whole as words, or spelled alike. Each name
        gets at most `limit` entities, and none when nothing is likely, so the
        caller sees a few candidates, never every entity.
        """
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if any(not isinstance(name, str) or not name.strip() for name in names):
            raise ValueError("each name must be non-empty text")
        found: dict[str, list[Entity]] = {name: [] for name in names}
        if not found:
            return found
        with self.index.connect() as con:
            forms = con.execute("SELECT slug, form FROM forms").fetchall()
            best = {}
            for name in found:
                asked = plain(name)
                scores = {}
                for slug, form in forms:
                    score = _score(form, asked)
                    if score >= LIKELY and score > scores.get(slug, 0):
                        scores[slug] = score
                best[name] = sorted(scores, key=lambda slug: (-scores[slug], slug))[:limit]
            wanted = sorted({slug for slugs in best.values() for slug in slugs})
            entities = {}
            for id, details, name in con.execute(
                "SELECT id, details, description FROM entries"
                " WHERE key IN (SELECT 'entity:' || value FROM json_each(?))",
                (json.dumps(wanted),),
            ):
                details = json.loads(details)
                entities[details["slug"]] = Entity(id, details["slug"], name, details.get("kind"), details["aliases"])
        for name, slugs in best.items():
            found[name] = [entities[slug] for slug in slugs]
        return found

    def known_slugs(self, slugs: list[str]) -> set[str]:
        """Those of `slugs` that some entity has been recorded under."""
        with self.index.connect() as con:
            rows = con.execute(
                "SELECT DISTINCT slug FROM records WHERE slug IN (SELECT value FROM json_each(?))",
                (json.dumps(list(slugs)),),
            ).fetchall()
        return {slug for (slug,) in rows}

    def read(self, ids: list[str]) -> list[dict]:
        """The full records for `ids`, in event-date order, each as it stands now.

        An entry comes with its revisions applied and its `amendments`, oldest
        first, under its body, which is never replaced; an entity comes as its
        statements hold it now. The id of a revision or of an older statement
        reads the entry it belongs to. An id not found is left out.
        """
        with self.index.connect() as con:
            rows = con.execute(
                f"SELECT {', '.join('id' if name == 'entry' else name for name in FIELDS)}, amendments"
                " FROM entries WHERE key IN ("
                "   SELECT CASE WHEN slug IS NOT NULL THEN 'entity:' || slug ELSE entry END"
                "   FROM records WHERE id IN (SELECT value FROM json_each(?))"
                " ) ORDER BY event_date, id",
                (json.dumps(list(ids)),),
            ).fetchall()
        return [_record(row) for row in rows]


def _match(pattern: str) -> str:
    """A pattern as an FTS5 query. Every term is quoted, so no character of it
    reaches FTS5's own syntax, and punctuation inside a term is searched as a word break."""
    groups, positive, negative = [], [], []
    for term in _TERM.finditer(pattern):
        if term[4] is not None:
            word = term[4]
            if word == "OR":
                groups.append((positive, negative))
                positive, negative = [], []
                continue
            excluded = word.startswith("-") and len(word) > 1
            word = word[1:] if excluded else word
            prefix = word.endswith("*")
            word = word.rstrip("*")
        else:
            excluded, word, prefix = bool(term[1]), term[2], bool(term[3])
        if not any(ch.isalnum() for ch in word):
            continue
        quoted = '"' + word.replace('"', '""') + '"' + ("*" if prefix else "")
        (negative if excluded else positive).append(quoted)
    groups.append((positive, negative))
    parts = []
    for positive, negative in groups:
        if negative and not positive:
            raise PatternError("a pattern needs a word to find, not only words to leave out")
        if positive:
            part = " AND ".join(positive)
            parts.append(f"(({part}) NOT ({' OR '.join(negative)}))" if negative else f"({part})")
    if not parts:
        raise PatternError("a pattern needs a word to find")
    return " OR ".join(parts)


def _ranges(days: list[tuple[str, int]]) -> list[tuple[str, str, int]]:
    """Consecutive event dates packed into ranges of at most the ceiling each. A
    single date past the ceiling is a range of its own, which dates cannot split."""
    ranges = []
    for day, count in days:
        if ranges and ranges[-1][2] + count <= CEILING:
            start, _, total = ranges[-1]
            ranges[-1] = (start, day, total + count)
        else:
            ranges.append((day, day, count))
    return ranges


def _snippets(con: sqlite3.Connection, rowids: list[int], match: str | None) -> dict[int, str]:
    """Each hit's snippet: around the best match in its body or its amendments,
    whichever matches more, or else the start of its body."""
    snippets = {}
    if match is not None and rowids:
        cut = f"'{_START}', '{_END}', '…', {SNIPPET_WORDS}"
        for rowid, body, amended in con.execute(
            f"SELECT rowid, snippet(words, 1, {cut}), snippet(words, 2, {cut}) FROM words"
            " WHERE words MATCH ? AND rowid IN (SELECT value FROM json_each(?))",
            (match, json.dumps(rowids)),
        ):
            text = max((body, amended), key=lambda text: text.count(_START))
            if _START in text:
                snippets[rowid] = _plain(text.replace(_START, "").replace(_END, ""))
    missing = [rowid for rowid in rowids if rowid not in snippets]
    if missing:
        for rowid, text, more in con.execute(
            f"SELECT rowid, substr(body, 1, {SNIPPET}), length(body) > {SNIPPET} FROM entries"
            " WHERE rowid IN (SELECT value FROM json_each(?))",
            (json.dumps(missing),),
        ):
            snippets[rowid] = _plain(text) + ("…" if more else "")
    return snippets


def _score(form: str, asked: str) -> float:
    """How well a form of an entity's name fits a name asked for: the same, one held
    whole in the other as words, or else how alike they are spelled."""
    if form == asked:
        return 1.0
    if f" {asked} " in f" {form} " or f" {form} " in f" {asked} ":
        return 0.9
    return jaro_winkler(form, asked)


def jaro_winkler(a: str, b: str) -> float:
    """The Jaro-Winkler similarity of two strings, from 0 to 1, with a common
    prefix of up to four characters raising it once it is above 0.7."""
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    window = max(len(b) // 2 - 1, 0)
    taken = [False] * len(b)
    matched = []
    for i, ch in enumerate(a):
        j = b.find(ch, max(0, i - window), i + window + 1)
        while j != -1 and taken[j]:
            j = b.find(ch, j + 1, i + window + 1)
        if j != -1:
            taken[j] = True
            matched.append(ch)
    m = len(matched)
    if not m:
        return 0.0
    transposed = sum(x != y for x, y in zip(matched, (ch for ch, t in zip(b, taken) if t))) / 2
    jaro = (m / len(a) + m / len(b) + (m - transposed) / m) / 3
    if jaro <= 0.7:
        return jaro
    prefix = 0
    for x, y in zip(a[:4], b[:4]):
        if x != y:
            break
        prefix += 1
    return jaro + prefix * 0.1 * (1 - jaro)


def _record(row: tuple) -> dict:
    record = dict(zip(FIELDS, row))
    record["details"] = json.loads(record["details"])
    record["amendments"] = json.loads(row[-1])
    return record


def _plain(text: str) -> str:
    return " ".join(text.split())


def _path(name: str) -> str:
    """A JSON path to a top-level field of `details`."""
    if '"' in name:
        raise ValueError(f"a details field name cannot hold a double quote: {name!r}")
    return f'$."{name}"'


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
