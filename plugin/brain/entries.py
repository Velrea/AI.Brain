"""One method per type the Brain supports, over the generic write.

Each fixes its type and version, takes only the fields that type has, and
packs what the type adds into `details`. The server exposes these, never
`Writer.write_entry` itself.
"""

from .write import Writer

JOURNAL_VERSION = 1


class Entries:
    def __init__(self, writer: Writer):
        self.writer = writer

    def write_journal(
        self, *, event_date: str, description: str, body: str, source: str | None = None
    ) -> str:
        """Records a journal entry: an account of what happened. Returns its id."""
        return self.writer.write_entry(
            type="journal",
            version=JOURNAL_VERSION,
            event_date=event_date,
            description=description,
            body=body,
            source=source,
        )
