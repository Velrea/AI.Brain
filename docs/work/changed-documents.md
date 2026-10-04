# Changed documents

**A filed document edited in place cannot be recorded again.** Handed back a document already in the Brain's documents, the document skill files it with `--move`, which its script refuses, since a filed document is never moved. Filing it at its own path without `--move` does return its new `sha256`, but nothing tells the model so, and the skill's rule that a changed document revises its entry with its new `sha256` has no way through.

## Suggested

- The refusal of a move inside the documents folder says to file the document at its own path without moving it, or the document skill files a document already there that way.

## Done when

- Handing over an edited filed document revises its document entry with its new `sha256`, with no refusal the model cannot get past.
