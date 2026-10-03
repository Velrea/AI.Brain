# Changed and pointer documents

Two gaps in filing a document.

**A filed document edited in place cannot be recorded again.** Handed back a document already in the Brain's documents, intake files it with `move: true`, which `store_document` refuses, since a filed document is never moved. Filing it at its own path with `move: false` does return its new `sha256`, but nothing tells the model so, and the intake skill's rule that a changed document revises its entry with its new `sha256` has no way through.

**A pointer file is filed as if it were the document.** Some files on disk are only a shortcut or a pointer to content kept elsewhere. Intake would file the pointer and record its hash, so the entry carries none of the content, and the hash stays the same when the content changes.

## Decided

- **A pointer is recorded as a pointer**, never filed as a document with content.
- **The skill names no product.** It describes pointer files in general, so it covers any technology that leaves one.

## Suggested

- The refusal of a move inside the documents folder says to file the document at its own path without moving it, or intake files a document already there that way.
- For a pointer, the content is read through whatever source the session can reach, the entry names where the content lives, and the pointer file itself is not filed.

## Done when

- Handing over an edited filed document revises its document entry with its new `sha256`, with no refusal the model cannot get past.
- Handing over a pointer file records an entry naming where its content lives, carrying the content where the session can reach it, and files no pointer.
