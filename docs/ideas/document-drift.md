# Document drift

Concerns documents, reading, and the journal.

Notice when a filed document no longer matches the `sha256` the journal entry recorded for it.

- **`read` reports drift; it never writes.** Reading an entry that names a document rehashes the document, and a mismatch is reported in what `read` returns. What to do about it is the model's call, and the skills equip it to record the change.
- **A mismatch is a signal, not an error.** The documents folder is organized for the user to browse, so a filed document can be opened and edited in place. A static file such as a PDF never changes; a working document such as a prep sheet can.
- **What it should have been is a new entry.** A document that changed after an entry recorded it is a new event, journaled with its new `sha256`, so the old entry's hash still says what the document was when it was written.
- **Rehashing reads the whole file.** In a synced folder whose files are cloud placeholders, that downloads them: fine for a few documents, slow for many.
