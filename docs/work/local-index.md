# The local index

Reading moves from scanning every event file on every call to a database each machine keeps for itself, built from the files and kept up to date as they arrive. The files stay the Brain; the index is a disposable projection of them. It makes a read a lookup instead of a scan, and it makes corrections possible without slowing reads: a correction is applied once, when it arrives, instead of on every read.

It replaces how [`Reader`](../../plugin/brain/read.py) finds entries, not what it answers: `search`, `read`, and `resolve` keep their shape.

## Decided

- **The files are unchanged and stay the truth.** Records are JSON lines, each machine appends only to files it created, and files roll and seal as now. The write path is the only thing that writes the synced folder.
- **Each machine keeps a SQLite index in its own state folder**, never synced. A database file in a synced folder is corrupted by the sync service copying it mid-write, and two machines would fork it into conflict copies.
- **The index is disposable.** It holds nothing the files do not. Missing, corrupt, or built by an older version, it is deleted and rebuilt from the files.
- **Every read catches up first.** The index keeps, for each file, how many bytes it has taken in, and reads only the complete lines past that. A sealed file is read once in its life, and a read with nothing new pays only for listing the folder. The watermark is per file because each machine's files grow on their own and arrive late; no single position covers them.
- **Corrections are records.** A `repair` names the entry it corrects by id and sets any of its `details`, description, or event date, never its body: the method that writes one takes no body for the target, and the index takes only those fields from a repair. For each field, the newest repair setting it wins, by id, so two machines repairing different fields of one entry both hold. A repair that arrives before its target waits for it.
- **The index collapses only corrections and restatements**: a repair into the entry it corrects, an entity's statements into one entity. Every journal entry stays its own row, and the files keep every event.
- **DuckDB is removed.** Python's own SQLite does the reading, so the plugin pins one package fewer.
- **No small-file compaction.** It existed because file count set read time when every read scanned every file. With the index, a sealed file is read once, so file count barely matters. Rolling stays: the sync service uploads a whole file on every change, so small files keep each upload small, and a sealed file is backed up once.
- **No facts recorded at write time.** Extracting structured facts, such as a current dose, would need every future question anticipated, and a fact extracted wrong is trusted silently. Entities find every entry on a subject without knowing the question, and a snapshot caches an expensive answer for a question actually asked.

## Done when

- `search`, `read`, and `resolve` answer from the index, and the read tests pass against it.
- A read takes in only the new complete lines of each file, and an index rebuilt from scratch answers the same as one caught up file by file.
- A `repair` is written through its own method, cannot change a body, and every read reflects it.
- The tests cover a repair arriving late, a repair arriving before its target, a torn last line, the same record in two files, a crash midway through catching up, a file that vanishes, and several sessions reading and writing at once.
- `duckdb` is gone from the plugin's requirements.

## Suggested

- **Search by words and phrases with SQLite's full-text index**, in place of regular expressions. SQLite has no fast regular expressions: one written in Python took about 500 ms over 200,000 entries, where a full-text search takes milliseconds. This changes what `search` accepts, so it is the call to settle first.
- **The writer updates its own machine's index** after appending, so the next read has nothing to catch up on.
- **Write-ahead logging**, so sessions on one machine read while another catches up.
- **Rebuild when a file vanishes or shrinks**, since the index cannot tell which of its rows came only from that file.
- **A snapshot knows when it is stale.** The index can tell which entities gained entries after a snapshot was taken, in place of reaching back a few days past its `recorded_at`.
- **Prototypes measured the direction**, over synthetic stores of a million entries: a SQLite index answered everything about one subject in about 10 ms and a word search in 7 to 45 ms, rebuilt from scratch in 20 to 60 seconds, and took about 2.5 times the files' size on disk. Scanning every file took about 140 ms a read before any corrections, and over 350 ms with them.
