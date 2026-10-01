"""One write method per type the Brain supports, over the generic write.

Each fixes its type and version, takes only the fields that type has, and
packs what the type adds into `details`, so the shape of a record is the
code's to control. The server exposes these, never `Writer.write_entry`
itself. Reading needs no such methods: `Reader` returns every type the same way.
"""

import datetime as dt

from .format import RecordError
from .write import Writer

JOURNAL_VERSION = 1
SNAPSHOT_VERSION = 1


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

    def write_snapshot(self, *, scope: str, description: str, body: str) -> str:
        """Records a folded answer so it need not be recomputed. Returns its id.

        `scope` is the question's meaning, put so paraphrases land on one
        scope. Written only at the user's word.
        """
        if not isinstance(scope, str) or not scope.strip() or scope.splitlines() != [scope]:
            raise RecordError("scope must be one line of non-empty text")
        return self.writer.write_entry(
            type="snapshot",
            version=SNAPSHOT_VERSION,
            # The day it was taken: a snapshot is an event in its own right.
            event_date=dt.date.today().isoformat(),
            description=description,
            body=body,
            details={"scope": scope},
        )
