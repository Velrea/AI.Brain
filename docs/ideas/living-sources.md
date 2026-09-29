# Living sources

Concerns [references](../data-format.md).

A reference to something that keeps changing, such as a web page or a shared online document, as opposed to a frozen file.

- **The Brain keeps** the address, a fingerprint of the version read, the summary in the body, and optionally an archived copy.
- **A living source is an entity, and each reading is a journal entry about it.** The fingerprint is the source's own revision id or last-edited time where it has one, else a hash of the fetched text. A change is a new reading, never an amendment.
- **A Google Doc or Sheet is a living source.** Its file on disk is a small pointer stub, so hashing the stub misses every change to the document.

Open: whether a living source is archived on every reading, only on request, or when the model judges the wording matters.
