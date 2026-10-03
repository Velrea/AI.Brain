# Living sources

Concerns file references and the journal.

A reference to something that keeps changing, such as a web page or a shared online document, as opposed to a filed document.

- **A living source is a reference on a journal entry, beside the document reference**, not an entity. An entry that read a web page names it by its address and a fingerprint of the version read, the way an entry about a filed document names it by path and `sha256`.
- **A change is a new reading**, journaled as a new entry, never an amendment.
- **The fingerprint is the hard part.** A file is hashed, but a page's raw HTML changes on every fetch with ads and per-request tokens. Where the source has its own version marker, such as a Google Doc's revision id or modified time, or an HTTP `ETag` or `Last-Modified`, that is the fingerprint; otherwise a hash of the page's extracted text.
- **The model does the fetching, not the server**, which has no network access. A fingerprint can only be what the fetching tool exposes: a cloud drive's revision or modified time, but no `ETag` from a web fetch, and a model cannot hash text reliably. Short of the server fetching pages itself, the version read is the tool's marker where it gives one, and otherwise the date it was read.

Open: how to fingerprint a page with no version marker of its own, so the same content reads as the same version.
