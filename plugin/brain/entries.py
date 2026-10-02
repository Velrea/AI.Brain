"""One write method per type the Brain supports, over the generic write.

Each fixes its type and version, takes only the fields that type has, and
packs what the type adds into `details`, so the shape of a record is the
code's to control. The server exposes these, never `Writer.write_entry`
itself. Reading needs no such methods: `Reader` returns every type the same way.
"""

import datetime as dt
import re
from collections.abc import Sequence

from .format import RecordError
from .index import REVISABLE
from .read import Reader
from .write import Writer

JOURNAL_VERSION = 1
SNAPSHOT_VERSION = 1
ENTITY_VERSION = 1

_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


class UnknownEntities(RecordError):
    """A journal entry named slugs no entity has been recorded under."""

    def __init__(self, slugs: list[str]):
        super().__init__(f"no entity is recorded as {', '.join(slugs)}: resolve or write it first")
        self.slugs = slugs


class Entries:
    def __init__(self, writer: Writer, reader: Reader):
        self.writer = writer
        self.reader = reader

    def write_journal(
        self,
        *,
        event_date: str,
        description: str,
        body: str,
        entities: Sequence[str] = (),
        source: str | None = None,
    ) -> str:
        """Records a journal entry: an account of what happened. Returns its id.

        `entities` are the slugs of the entities the entry is about, each
        one an entity already recorded, or UnknownEntities is raised and
        nothing is written. Entities are never removed, so a slug found
        here is still there when the entry is written.
        """
        entities = self._known("entities", entities)
        return self.writer.write_entry(
            type="journal",
            version=JOURNAL_VERSION,
            event_date=event_date,
            description=description,
            body=body,
            source=source,
            details={"entities": entities} if entities else {},
        )

    def revise_journal(
        self,
        entry: str,
        *,
        description: str | None = None,
        event_date: str | None = None,
        entities: Sequence[str] | None = None,
        amendment: str | None = None,
        source: str | None = None,
    ) -> str:
        """Revises a journal entry and returns the revision's id.

        `description`, `event_date`, and `entities` replace the entry's, and
        each one not given is left as it stands. The body is never replaced:
        `amendment` is kept under it, such as "Correction: it was three drops,
        not two.", so the account stays as it was given and the correction
        travels with it. `entry` is the id of the original entry. Raises
        RecordError when nothing is revised or `entry` is not a journal
        entry, and UnknownEntities as `write_journal` does.
        """
        given = {"description": description, "event_date": event_date, "entities": entities}
        revises = [name for name in REVISABLE if given[name] is not None]
        if not revises and amendment is None:
            raise RecordError("a revision must change the description, event date, or entities, or add an amendment")
        if amendment is not None and (not isinstance(amendment, str) or not amendment.strip()):
            raise RecordError("amendment must be non-empty text")
        current = next((record for record in self.reader.read([entry]) if record["id"] == entry), None)
        if current is None or current["type"] != "journal":
            raise RecordError(f"no journal entry has the id {entry!r}")
        details = {"revises": revises}
        if entities is not None:
            details["entities"] = self._known("entities", entities)
        return self.writer.write_entry(
            entry=entry,
            type="journal",
            version=JOURNAL_VERSION,
            # Whole on its own: what it does not revise is the entry's as it stood.
            event_date=current["event_date"] if event_date is None else event_date,
            description=current["description"] if description is None else description,
            body=amendment or "",
            source=source,
            details=details,
        )

    def _known(self, name: str, slugs: object) -> list[str]:
        """The slugs, each checked as one an entity is recorded under."""
        slugs = _slugs(name, slugs)
        missing = sorted(set(slugs) - self.reader.known_slugs(slugs)) if slugs else []
        if missing:
            raise UnknownEntities(missing)
        return slugs

    def write_snapshot(self, *, scope: str, description: str, body: str) -> str:
        """Records a folded answer so it need not be recomputed. Returns its id.

        `scope` is the question's meaning, put so paraphrases land on one
        scope. Written only at the user's word.
        """
        _one_line("scope", scope)
        return self.writer.write_entry(
            type="snapshot",
            version=SNAPSHOT_VERSION,
            # The day it was taken: a snapshot is an event in its own right.
            event_date=dt.date.today().isoformat(),
            description=description,
            body=body,
            details={"scope": scope},
        )

    def write_entity(
        self,
        *,
        slug: str,
        name: str,
        kind: str,
        body: str,
        aliases: Sequence[str] = (),
        source: str | None = None,
    ) -> str:
        """Records an entity: a person, thing, or topic entries are about. Returns its id.

        Entries name it by `slug`. `name` is what it is called, `kind` what
        sort of thing it is, such as person or medication, and `aliases` the
        other names it goes by. Writing a slug already recorded restates
        that entity: its name, kind, and body become the newest statement's,
        and its aliases add to those already recorded.
        """
        _slug("slug", slug)
        _one_line("name", name)
        _one_line("kind", kind)
        return self.writer.write_entry(
            type="entity",
            version=ENTITY_VERSION,
            # The day it was stated: an entity is restated, never edited.
            event_date=dt.date.today().isoformat(),
            description=name,
            body=body,
            source=source,
            details={"slug": slug, "kind": kind, "aliases": _lines("aliases", aliases)},
        )


def _one_line(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip() or value.splitlines() != [value]:
        raise RecordError(f"{name} must be one line of non-empty text")


def _slug(name: str, value: object) -> None:
    if not isinstance(value, str) or _SLUG.fullmatch(value) is None:
        raise RecordError(f"{name} must be a slug, such as dr-jekyll: {value!r}")


def _lines(name: str, values: object) -> list[str]:
    """Each value checked as one line of text, once each, in the order given."""
    if isinstance(values, str) or not isinstance(values, Sequence):
        raise RecordError(f"{name} must be a list")
    for value in values:
        _one_line(name, value)
    return list(dict.fromkeys(values))


def _slugs(name: str, values: object) -> list[str]:
    values = _lines(name, values)
    for value in values:
        _slug(name, value)
    return values
