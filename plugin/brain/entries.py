"""The one write for every type: creates an entry, or revises one.

What a type means is its skill's: the type and its version are the caller's
to give, and its own fields go in `details`. What every entry obeys is checked
here against what is already recorded: a new entry's slug is one no entry
carries, each link names a slug some entry carries, and a revision names an
entry of its own type. The server exposes this, never `Writer.write_entry`.
"""

from collections.abc import Mapping, Sequence

from .documents import DOCUMENT, check_document
from .format import REVISABLE, RecordError, check_slug
from .read import Reader
from .write import Writer


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


class Entries:
    def __init__(self, writer: Writer, reader: Reader):
        self.writer = writer
        self.reader = reader

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
        """
        aliases = _lines("aliases", aliases)
        if links is not None:
            links = self._linked(links)
        if details is not None and not isinstance(details, Mapping):
            raise RecordError("details must be an object of fields")
        details = dict(details or {})
        if entry is None:
            return self._create(type=type, version=version, slug=slug, event_date=event_date,
                                description=description, body=body, links=links or [], aliases=aliases,
                                details=details, source=source)
        if slug is not None:
            check_slug("slug", slug)
        given = {"description": description, "event_date": event_date, "links": links}
        revises = [name for name in REVISABLE if given[name] is not None]
        if not (revises or slug or aliases or details or body is not None):
            raise RecordError("a revision must change the description, event date, links, slugs, aliases, or"
                              " details, or add an amendment")
        if body is not None and (not isinstance(body, str) or not body.strip()):
            raise RecordError("an amendment must be non-empty text")
        current = next((record for record in self.reader.read([entry])), None)
        if current is None:
            raise RecordError(f"no entry has the id {entry!r}")
        if current["type"] != type:
            raise RecordError(f"entry {current['id']} is a {current['type']}, not a {type}")
        if type == DOCUMENT and details:
            check_document({
                name: value for name, value in {**current["details"], **details}.items() if value is not None
            })
        return self.writer.write_entry(
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

    def _create(self, *, type, version, slug, event_date, description, body, links, aliases, details,
                source) -> str:
        check_slug("slug", slug)
        if type == DOCUMENT:
            check_document(details)
        if holders := self.reader.holders([slug]).get(slug):
            raise SlugTaken(slug, holders)
        return self.writer.write_entry(
            type=type, version=version, event_date=event_date, description=description, body=body,
            source=source, slugs=[slug], aliases=aliases, links=links, details=details,
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


def _lines(name: str, values: object) -> list[str]:
    """Each value checked as one line of text, once each, in the order given."""
    if isinstance(values, str) or not isinstance(values, Sequence):
        raise RecordError(f"{name} must be a list")
    for value in values:
        if not isinstance(value, str) or not value.strip() or value.splitlines() != [value]:
            raise RecordError(f"{name} must each be one line of non-empty text")
    return list(dict.fromkeys(values))
