# The core module

The Python package that is the Brain's low-level interface to its data, and the first thing built. It defines the shape of a record and the layout of the folders, and it holds the write path. The MCP server imports it and wraps it; tests exercise it directly, with no server.

A Brain is an append-only log of events: it holds events, never current state, and how things stand now is worked out by reading the events in order. Every entry is appended through this module, so capture and corrections both depend on it: a record is never edited, and a correction is a new entry.

This item builds the write path. The read path in the diagram is [reading](reading.md), which extends this package later, so it is laid out for reading from the start.

```mermaid
flowchart LR
    agent([Agent])

    subgraph write [Write path]
        validate[Validate the record,<br/>stamp its id] --> lock[Take the<br/>file lock] --> append[Append<br/>one line]
    end

    files[("event store<br/>*.jsonl")]

    subgraph read [Read path]
        duckdb[DuckDB reads<br/>the event store] --> query[Query] --> results[Paged results]
    end

    agent --> validate
    append --> files
    files --> duckdb
    results --> agent
```

## Settled

- **One package, with writing and reading in separate modules** and a shared module for the record's shape and the folders' layout. The write path never loads DuckDB. The read side depends on the file format alone, never on the writer's internals.
- **Only this module writes the files**, appending under a lock and never through DuckDB: DuckDB cannot append to a JSONL file, and a DuckDB database allows only one writing process. It validates each record against the fields below and stamps its id. A person or a model never edits a file by hand; an agent reaches the files only through the server, which calls this module.
- **Two folders are configured**: the event store for the records, and the documents store for filed documents.
- **The event store is one flat `events/` folder, and each file is owned by the machine that created it**, so no two machines append to one file and no machine is named in the layout. A file is named `h-<uuidv7>.jsonl` when it is created, and only its creator ever appends to it. The machine keeps the name of its current file in machine-local state, outside the synced folders.
- **A machine whose file is gone, or whose local state is missing or does not match the store, starts a new file** and records it. It never resumes a file it did not create.
- **A file rolls when it reaches 10,000 lines or is 7 days old**, by the time in its name. The machine starts a new file, and the old one is sealed and never changes again, so a backup or a sync copies it once. When a file rolls carries no meaning for a reader. The `h-` prefix and the 7-day roll leave room for compacting small files later.

```
<event store>/
  events/
    h-0199a8c4-….jsonl      sealed: its machine has moved on
    h-0199f02e-….jsonl      open: its machine appends here

<documents store>/           filed documents

<machine-local state>/       outside the synced folders
                             the lock file, and this machine's current file
```

- **Sessions on one machine take turns through an OS lock on a separate lock file.** The lock file sits in machine-local state, named for the event store's path so two Brains never share one; the lock coordinates only one machine, so it has no reason to sync. Only the OS lock counts: the file's existence means nothing, and the OS releases the lock when its process dies, so a crash leaves no stale lock. A JSONL file is never locked itself: the holder may roll it, and on Windows a lock on a file's bytes blocks everyone else from reading them.
- **A session that cannot take the lock waits**, and gives up with an error after about 30 seconds. The lock is held for milliseconds, so a longer wait means something has hung.
- **The holder leaves the store ready for the next writer**, rolling a file that is due before it releases the lock. A writer that takes the lock still checks what it finds, because a holder that crashed left no promises: it ends a torn last line and rolls a file that is due.
- **An append blocked by the sync service retries with backoff, under the lock.** A local outbox is held in reserve in case retries prove not enough: records wait in a file outside the synced folders, and the next writer to take the lock appends them first, in order. The sync service's behaviour is not tested. The Brain relies on it and does not coordinate machines, so minor loss at the sync boundary is accepted.
- **Each record is one line of JSON** in UTF-8, ended by a newline, with its fields at the top level and no wrapping payload object.

```json
{"id":"0199a8c4-…","type":"journal","version":1,
 "recorded_at":"2026-09-28T23:14:32Z","event_date":"2026-09-14",
 "description":"Oil change","source":"voice",
 "body":"## Service\nOil and filter changed…"}
```

Every field is required unless marked optional.

| Field | Carries |
| --- | --- |
| `id` | A UUIDv7. Unique everywhere without coordination. It carries no meaning a query relies on. |
| `type` | The kind of entry, such as `journal`. Every record is an entry; `type` says which kind. |
| `version` | The version of that type's shape the record was written under. |
| `recorded_at` | When it was written down, UTC. For display; nothing orders by it for correctness. |
| `event_date` | When the event happened, local date. What a reader orders by. |
| `description` | One-line summary. |
| `body` | Markdown: the account itself, and everything else the record holds. |
| `source` | How the information arrived, free text, such as `voice` or `email`. Optional. |

- **A record carries no writer and no position.** Its `id` makes it stand alone wherever it is copied, and a snapshot marks what it has read by lines per file.
- **A record is never edited.**
- **An append is one whole line.** A writer that finds its open file ending without a newline, from a crash mid-append, ends that fragment with a newline before appending. It never truncates.

## Done when

- Concurrent sessions on one machine each append whole lines, and no two lines interleave.
- A file whose last line is torn gets that line ended with a newline before the next append.
- A file that reaches 10,000 lines, or is 7 days old, is left, and the next append goes to a new file.
- A machine whose file is gone, or whose local state is missing, starts a new file and never appends to one it did not create.
- A session that cannot take the lock within the timeout gets an error, and a process that dies holding the lock leaves nothing that blocks the next one.
- An append blocked by another process holding the file open retries, and succeeds once the file is released.
- A record missing a required field, or setting one the module stamps, is rejected.
- The tests drive the module directly, with no server.
- The record's shape and the folders' layout sit in the shared module, where the read side can import them.
