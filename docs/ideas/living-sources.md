# Living sources

Concerns file references and the journal.

A reference to something that keeps changing, such as a web page or a shared online document, as opposed to a filed document.

- **A living source is a reference on a journal entry, beside the document reference**, not an entity. An entry that read a web page names it by its address, the way an entry about a filed document names it by path.
- **Nothing is copied into the Brain.** A website stays where it is; the entry keeps the address, a fingerprint of the version read, and a summary in its body.
- **A change is a new reading**, journaled as a new entry, never an amendment.
- **The fingerprint is the hard part.** A file is hashed, but a page's raw HTML changes on every fetch with ads and per-request tokens. Where the source has its own version marker, such as a Google Doc's revision id or modified time, or an HTTP `ETag` or `Last-Modified`, that is the fingerprint; otherwise a hash of the page's extracted text.
- **A Google Doc or Sheet is a living source.** Its file on disk is a small pointer stub, so hashing the stub misses every change to the document.

Open: how to fingerprint a page with no version marker of its own, so the same content reads as the same version.
