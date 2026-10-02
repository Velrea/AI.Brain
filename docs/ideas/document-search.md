# Document search

Concerns reading and documents.

Search inside filed documents and load only the part that matched, the way grep and a read of a few lines work on files on disk.

- **Journal entries do not need it.** A record is one line of JSON with its body a single escaped string, so a line number means nothing inside it, and most entries are a few hundred words: a slice barely beats the whole. Pointing a caller at raw file offsets would hand it escaped JSON and bypass the revisions the index applies.
- **Filed documents do.** A 40-page policy or a lab report is where loading the whole thing bloats the context. Their text could be indexed by section or page, with pointers back to the file, so a search finds the deductible clause and a read loads the page around it.
- **The same shape could serve entries' sections**, since bodies are Markdown with headings: a hit naming the section that matched, and a read returning just that section. Worth it only if entries grow long, such as pasted emails or long dictations.
