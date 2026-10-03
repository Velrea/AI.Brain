# Document drift

Concerns documents and the journal.

A check that rehashes every document the journal names and lists those whose contents no longer match the `sha256` the entry recorded.

- **A mismatch is a signal, not an error.** An entry names a document by path and `sha256`, so if the file at that path changes, or a different file is put there under the same name, the hash says so. A static file such as a PDF never changes; a working document such as a prep sheet or a chart does.
- **What it should have been is a new entry.** A document that changed after an entry recorded it is a new event, and the check is how one that went unrecorded is caught, so it can be journaled then.
