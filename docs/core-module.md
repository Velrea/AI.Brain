# The core module

The Python package in [`plugin/brain/`](../plugin/brain/) is the Brain's low-level interface to its data. It defines the shape of a record and the layout of the folders, and it holds the write path and the read path. Nothing else writes the files: an agent reaches them only through the MCP server, which calls this package. Reading goes through [a local index](#the-local-index) each machine builds from the files and keeps for itself. The tests in [`tests/`](../tests/) drive it directly, with no server.

A Brain is an append-only log of events. It holds events, never current state; how things stand now is worked out by reading the events in order. A record is never edited, and a correction is a new record.

| Module | Holds |
| --- | --- |
| [`format.py`](../plugin/brain/format.py) | The file format: the record's envelope and its checks, the one-line encoding, the folder layout, and file names. The read side imports it; it imports neither side. |
| [`write.py`](../plugin/brain/write.py) | `Writer.write_entry`, the one generic write. |
| [`index.py`](../plugin/brain/index.py) | The local index: the SQLite database this machine keeps of the files, caught up before every read. |
| [`read.py`](../plugin/brain/read.py) | `Reader`, the one read for every type: search, and full records by id, and resolving names to [entities](#entities). It reads through the index and imports the file format, never the write path. |
| [`entries.py`](../plugin/brain/entries.py) | One write method per supported type, over `write_entry`, and `revise_journal`. |
| [`lock.py`](../plugin/brain/lock.py) | The OS lock that makes sessions on one machine take turns. |

## Folders

```
<event store>/                 synced between machines
  events/
    h-0199a8c4-….jsonl         sealed: its machine has moved on
    h-0199f02e-….jsonl         open: its machine appends here

<state folder>/                this machine's own, never synced
  <key>.lock                   the lock file
  <key>.json                   the file this machine appends to, and its line count
  <key>.index-v1.sqlite        the local index
```

The event store is one flat `events/` folder. Each file is named `h-<uuidv7>.jsonl` for the time it was started, and only the machine that created it ever appends to it. A sync service copies whole files between machines, so two machines appending to one file would each overwrite the other's lines; with one owner per file, that never happens, and no machine is named in the layout. The state folder is never synced: the lock coordinates only this machine, the current file is this machine's alone, and the index is built here from the files. `<key>` is a hash of the event store's path, so two Brains on one machine never share a lock, a current file, or an index. The caller hands the `Writer` and the `Reader` both folders; the MCP server supplies the state folder.

## A record

Each record is one line of UTF-8 JSON, ended by a newline, with one envelope shared by every type. What a type adds goes in `details`, never beside the envelope, so every record has the same shape whatever its type: the read side's columns are fixed, and nothing a type adds can clash with a field of the envelope.

```json
{"id":"0199a8c4-…","entry":"0199a8c4-…","type":"journal","version":1,
 "recorded_at":"2026-09-28T23:14:32Z","event_date":"2026-09-14",
 "description":"Oil change","source":"voice",
 "body":"## Service\nOil and filter changed…","details":{}}
```

| Field | Carries |
| --- | --- |
| `id` | A UUIDv7, stamped by the write path. Unique everywhere without coordination; it carries no meaning a query relies on. |
| `entry` | The entry the record belongs to: its own `id` on an original, the original's on a [revision](#revisions). Stamped by the write path, and never empty, so every record has the same shape. |
| `type` | The kind of entry, such as `journal`. |
| `version` | The version of that type's shape the record was written under, fixed by the type's method. |
| `recorded_at` | When it was written down, UTC, stamped by the write path. For display and for finding what changed since; nothing orders by it. |
| `event_date` | When the event happened, a local date. What a reader orders by. |
| `description` | A one-line summary. |
| `body` | Markdown: the account itself. |
| `source` | How the information arrived, such as `voice` or `email`. The only optional field. |
| `details` | What the type adds, as a JSON object; `{}` when it adds nothing. |

A record carries no writer and no position: its `id` lets it stand alone wherever it is copied. The newline ends a record. A line that is whole and valid JSON is a record, and anything else is a fragment a reader skips.

## Writing

A caller writes through a type's method, such as `Entries.write_journal`, which takes only that type's fields, fixes its `type` and `version`, and calls `Writer.write_entry`. The MCP server exposes the type methods, never `write_entry`. The types so far are `journal`, [`entity`](#entities), and [`snapshot`](#snapshots), and a journal entry is corrected through [`revise_journal`](#revisions). A journal entry names the entities it is about, by slug, in `details.entities`, and `write_journal` refuses a slug no entity has been recorded under, with `UnknownEntities`, so an entry never names a subject nothing can resolve. Entities are never removed, so the check, made before the lock, cannot go stale.

```mermaid
flowchart LR
    method["write_journal"] --> check["Check the envelope"]
    check --> lock["Take the lock"]
    lock --> stamp["Stamp id, entry,<br/>and recorded_at"]
    stamp --> current["Find this machine's file:<br/>end a torn line,<br/>roll one that is due"]
    current --> append["Append one line,<br/>synced to disk"]
    append --> roll["Roll the file<br/>if now due"]
    roll --> release["Release the lock"]
```

- **Checks.** A blank or invalid envelope field, or `details` that is not a JSON object, raises `RecordError`, and nothing is written.
- **The lock.** An OS lock on the lock file in the state folder, never on a JSONL file: the holder may roll the file, and on Windows a lock on a file's bytes blocks everyone else from reading them. A session waits up to 30 seconds, then gets `LockTimeout`; the lock is held for milliseconds, so a longer wait means something has hung. The OS releases the lock when its process dies, so a crash leaves nothing behind.
- **This machine's file.** The state names the file and its line count. A file that is gone, or state that is missing or names another store, starts a new file; the machine never resumes a file it did not create.
- **A torn last line**, left by a crash mid-append, is ended with a newline before the next append. The fragment is never truncated: cutting bytes from a file the sync service may be copying can lose data.
- **Rolling.** A file rolls at 10,000 lines or 7 days old, by the time in its name. It is then sealed and never changes again, so a backup or a sync copies it once. The next append starts a new file. When a file rolls carries no meaning for a reader. Small files are never compacted into larger ones: the index reads a sealed file once, so how many there are barely matters to reading, and the sync service uploads a whole file on every change, so small files keep each upload small.
- **The append** is one unbuffered write, synced to disk before `write_entry` returns.
- **A blocked file.** An append that another process blocks, such as a sync service holding the file open, retries with backoff for up to 10 seconds under the lock, then raises `AppendBlocked`.

The Brain relies on the sync service to carry files between machines and does not coordinate them, so minor loss at the sync boundary is accepted.

## Reading

Writing is typed and reading is not. A type's write method controls the shape of what is recorded, so a caller never builds a record by hand; reading needs no such control, so `Reader` finds and returns entries of every type the same way, and the caller interprets what comes back by its type. Two calls cover it: `search` finds, `read` returns. Only `resolve`, which turns names into [entities](#entities), knows a type. They carry the mechanics of the index, so a caller needs only to know what to ask.

### The local index

Every read comes from a SQLite database this machine keeps in its state folder, built from the files and caught up with them before each read. The files stay the Brain, and the index is a disposable projection of them: it holds nothing they do not, and an index that is missing, corrupt, or built by another version is deleted and rebuilt from them. It makes a read a lookup instead of a scan of every file, and it lets a correction be applied once, when it arrives, instead of on every read. It is never in the synced folders: a sync service copying a database mid-write corrupts it, and two machines would fork it into conflict copies. Reading never writes the event store.

```mermaid
flowchart LR
    list["List the event files"] --> grown{"A file grown<br/>past its offset?"}
    list -- "a file vanished<br/>or shrank" --> rebuild["Rebuild from<br/>every file"]
    rebuild --> grown
    grown -- yes --> take["Take in its new<br/>complete lines"]
    take --> settle["Settle every entry<br/>they touch"]
    settle --> offset["Move its offset"]
    offset --> grown
    grown -- "no more" --> answer["Answer from the index"]
```

- **Catching up.** The index keeps, for each file, how many bytes of it it has taken in, and takes in only the complete lines past that. A sealed file is read once in its life, and a read with nothing new pays only for listing the folder. The offset is per file because each machine's files grow on their own and arrive late; no single position covers them. A file is taken in within one transaction, with its new offset, so a crash midway loses nothing and the next read carries on.
- **Bad lines.** A line that is not valid JSON, a torn line among them, or that lacks a field of the envelope is skipped, never reported as an error. A last line not yet ended by its newline waits until it is, since it may be an append in progress.
- **Each id once.** A record copied into two files is the same record, and is kept once.
- **Settling.** The index keeps every record, and beside them each entry as it stands now: an original with its [revisions](#revisions) applied, or an entity's statements as [one entity](#entities). Only revisions and restatements collapse: every entry is its own row, and the files keep every record.
- **A file that vanishes or shrinks** rebuilds the index, since it cannot tell which of its rows came only from that file.
- **Sessions.** Sessions on one machine share the index. Its write-ahead log lets them read while another takes in a file, and one waits up to 30 seconds for another to finish taking in. A change to the index's own layout names a new file, so sessions running two versions of the plugin never rebuild each other's.
- **SQLite is Python's own**, so the plugin pins no database package. It must include FTS5 full-text search and JSON, as the builds from python.org and most Linux distributions do; without them a read raises `IndexUnavailable`.

### Search and read

- **Order is `event_date`**, then `id` to break ties, never `recorded_at` or file position: records from different files interleave only by what they say.
- **`search`** finds words, in any case, in the description, the body, and the amendments of every type, or [entities](#entities) by slug, or both. Every word must appear, in any form of it, so `drop` finds "drops"; a "quoted phrase" must appear as written; a word or phrase ending in `*` matches as a prefix; one starting with `-` must not appear; and `OR` between terms finds either side. Accents are read as plain letters. Each term is quoted before it reaches SQLite's full-text search, so punctuation, as in `Dr. J` or `drop-off`, is never syntax. A pattern with nothing to look for raises `PatternError`. Words are searched through a full-text index rather than matched as regular expressions: SQLite has no fast regular expressions, and one written in Python took about 500 ms over 200,000 entries where a full-text search takes milliseconds.
- `search` filters by type, by event dates, inclusive, by `recorded_after`, a UTC time, which finds entries recorded or revised after it, and by exact `details` fields. It returns every hit, oldest first unless asked for newest first, each a lean one: its id, type, event date, recorded time, description, and a snippet of about 25 words around the best match in the body or its amendments, or else the first 160 characters of the body. A caller reads the hits, searches again where it needs more, and reads full text only for the ids it picks.
- **No paging, but a ceiling.** A search that finds more than 100 entries returns none and raises `TooManyHits`, with the total and how to refine it: more words or entities, types or details, more targeted searches, or event-date ranges that each fit within the ceiling. A page invites a caller to stop at the first one, and with results ordered by date the first page is the oldest; with no partial result, a caller never mistakes part of an answer for the whole of it. A hundred lean hits come to about 10,000 tokens.
- **`read`** returns the full records for a list of ids in one call, as objects in the envelope's shape with `details` parsed and an entry's `amendments` added, in event-date order. A revision's id, or an older statement's, reads the entry it belongs to. An id not found is left out.

With 200,000 records in 24 files, a search by entity takes about 8 ms, by a rare word about 50 ms, and a read of 20 ids about 3 ms. A word found in nearly every entry is the slow case, at about half a second. Building the index from scratch takes about 22 seconds, and it is 2.4 times the size of the files. At a million records, a search by entity still takes about 10 ms and a phrase about 3 ms, but a word found in 6% of entries takes about 340 ms, and a build from scratch about three and a half minutes.

### Revisions

A journal entry is corrected by a revision: a journal record whose `entry` names the original, written through `Entries.revise_journal`. It has its own method beside `write_journal` because the two take different things: a revision needs the entry it revises and accepts only what changes, where a new entry needs a body, a description, and a date. `entry` always names the original, never another revision, so no chain forms.

```json
{"id":"0199b0e1-…","entry":"0199a8c4-…","type":"journal",…,"event_date":"2026-09-14",
 "description":"Oil change and tyre rotation","body":"Correction: the tyres were rotated too.",
 "details":{"revises":["description"]}}
```

- **Metadata is replaced, newest per field.** `details.revises` names the fields a revision sets, of `description`, `event_date`, and `entities`. For each field, the newest revision setting it wins, by id, so two machines revising different fields of one entry before they sync both hold. The fields a revision does not set hold the entry's as they stood, so the record reads whole on its own.
- **A body is never replaced.** A revision's body is an amendment, kept under the original in the order recorded, so the account stays exactly as it was given and the correction travels with it: a search finds the entry by either text, and reading it returns the original with every amendment. A revision of metadata alone has an empty body.
- **A revision that arrives before its original** waits for it, and applies when it comes.

### Entities

An entity is a person, thing, or topic entries are about, such as `dr-jekyll`, `zorblax`, or `mom`. Searching text cannot promise every entry on a subject: an entry that says "two drops of Moonberry extract with breakfast" never says "medication". Naming an entry's entities when it is written moves that judgment to the moment a model looks at one entry with its whole attention, and a search by entity then returns the whole set in one call. Over a fictional decade of entries, three models asked which medications were current missed or misstated one with text search alone, and all three answered fully searching by subject.

An entity is an entry of type `entity`, written through `Entries.write_entity`, never a list kept beside the log: a list of every subject loaded on every write costs tokens that grow with the vocabulary, while entities in the log are queried, so only the likely matches come back. Its description is its name, its body says what it is, and its `details` carry its `slug`, its `kind`, such as `person` or `medication`, and its `aliases`, the other names it goes by. Entries name it by slug. A record is never edited, so writing a slug again restates the entity, with its event date the day it was stated. The index holds an entity's statements as one entity, since an entity is identified by its slug: its id, name, kind, and body are the newest statement's, by event date and then id, and its aliases are every statement's. Two machines that each add an alias before they sync lose neither, and a machine that has not yet seen an entity and records it again only adds to it.

```json
{"type":"entity","description":"Dr. Jekyll","body":"The family physician.",
 "details":{"slug":"dr-jekyll","kind":"person","aliases":["Dr. J"]}, …}
```

- **`resolve`** takes a list of names and returns, for each, up to five likely entities, best first, as each holds now: id, slug, name, kind, and aliases. A name is compared with an entity's slug, name, and aliases in any case, with punctuation and hyphens read as spaces. The same is the best match, then one held whole in the other as words, such as `jekyll` in `dr jekyll`, then one spelled alike by Jaro-Winkler similarity of at least 0.8. A name with nothing likely gets none. A writer passes every subject it finds in an entry, reuses an entity that matches, and creates one only when none does, so a subject is recorded once. Shorthand that spells nothing like the name, such as `meds` for `medication`, is found only through an alias.
- **Search by entity** returns the entries that name any of the slugs, and each entity itself, once. Given words as well, an entry is a hit when either finds it: requiring both would lose an entry whose entities were missed when it was written.

With 2,000 entities, resolving ten names takes about 160 ms, and with 10,000 about 770 ms, most of it comparing spellings in Python.

### Snapshots

A snapshot records a folded answer so it need not be recomputed, such as a list of the dragon's current hoard drawn from years of entries. It is an entry of type `snapshot`, written through `Entries.write_snapshot`, and only at the user's word. Its body holds the answer, its event date is the day it was taken, and its `details` carry `scope`, the question's meaning, put so paraphrases land on one scope.

A snapshot needs no read of its own. A caller finds the latest one for a question with `search`, then searches for what was recorded or revised after it, reaching back a few days past its `recorded_at` for entries that synced late, and folds those in. The reach-back is the caller's to choose.

A record that syncs later than the reach-back is missed, and so is a record the model misread when folding. Both are accepted: a machine with no connection cannot reach the model to record anything, so a long delay is rare, and any store kept in step by a sync service has the same gap. Either is fixed the same way, by building the snapshot afresh from every matching entry and writing a new one.

Nothing extracts facts, such as a current dose, when an entry is written. Extracting them would need every future question anticipated, and a fact extracted wrong is trusted silently. Entities find every entry on a subject without knowing the question, and a snapshot caches an expensive answer for a question actually asked.
