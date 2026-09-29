# The Brain data format

A Brain is an append-only log of events, kept as JSON Lines files, beside a folder of the documents those events rest on. It holds events, never current state; how things stand now is worked out by reading the events in order.

## Layout

```
<event store>/
  events/
    desktop-7f3a9c/
      writer.json            the machine name the writer was created on, and the software version
      000001.jsonl           sealed, never changes again
      000002.jsonl           open, the only file this writer appends to
    laptop-c91e02/
      writer.json
      000001.jsonl

<documents store>/           filed documents, at the paths file references name
```

- **A writer is one stream of files**, in its own folder under `events/`, named by its writer id. Only that writer ever changes its folder.
- **A writer id** is lowercase kebab-case, unique across the Brain, such as `desktop-7f3a9c`.
- **A stream's files are numbered** with six zero-padded digits, from `000001.jsonl`. The highest-numbered file is open; every other file is sealed and never changes again. When a file rolls carries no meaning for a reader.
- **Every writer folder is read on every read.** A writer that has gone quiet can come back.

## Records

Every line is one JSON object in UTF-8, ended by a newline: reserved envelope keys beside the type's properties at the top level, with no wrapping payload object.

```json
{"id":"0199a8c4-…","type":"journal-entry","v":1,"writer":"desktop-7f3a9c","seq":4127,
 "recorded_at":"2026-09-28T23:14:32Z",
 "date":"2026-09-14","description":"Oil change","source":"voice",
 "entities":["family-car"],
 "references":[{"kind":"file","path":"vehicles/family-car/2026-09-14-invoice.pdf","sha256":"…"}],
 "body":"## Service\nOil and filter changed…"}
```

| Field | Carries |
| --- | --- |
| `id` | A UUIDv7. Unique everywhere without coordination, and what every reference names. It carries no meaning a query relies on. |
| `type`, `v` | The type the record is an instance of, and the version of that type's definition it was written under. |
| `writer` | The stream the record belongs to, repeated from the folder so a record stands alone wherever it is copied. |
| `seq` | The record's position in its writer's stream: one more than the writer's previous record, continuing across files and never reset. |
| `recorded_at` | When it was written down, UTC. For display; nothing orders by it for correctness. |
| `date` | When the event happened, local date. What a reader orders by. |
| `description` | One-line summary. |
| `body` | Markdown, the account itself. |
| `entities` | Slugs of the durable things the entry is about. |
| `references` | Files the entry rests on; see References. |
| `amends` | The id of an earlier entry this one corrects or extends. Omitted when none. |
| `source` | How the information arrived, free text, such as `voice` or `email`. Optional. |

## Types

Every type extends `journal-entry`, which is the envelope and the fields above:

```
journal-entry        the envelope and the fields above
├─ snapshot          + scope, read_upto
└─ definition        + name, version, extends, properties, required; body = instructions for the model
```

- **A type is defined by a `definition` record** in the Brain itself, so a Brain carries the definitions its records were written under. `definition` is the one type a reader interprets natively.
- **A definition extends exactly one other and inherits its properties**, and may not redefine an envelope key or an inherited property. A record is valid when it satisfies its definition and every definition above it.
- **A type's format evolves by version.** `v` rises when a definition changes, and a reader translates older versions as it reads them.

## Writing

- **A record is never edited or removed.** A correction is a new entry naming the old one in `amends`, and the newer one wins.
- **An append is one whole line.** A writer that finds its open file ending without a newline, from a crash mid-append, ends that fragment with a newline before appending. It never truncates.
- **`seq` is taken from the writer's own last valid line**, so a number is used only once its line is on disk.

## Reading

- **A line that is not valid JSON is skipped.** A trailing line with no newline is still being written.
- **A duplicate `(writer, seq)` is flagged**, and a gap in a writer's `seq` is reported.
- **Order is `date`, not `recorded_at` or file position.** Streams from different writers interleave only by what the records say.

## References

| Kind | Example | What the Brain keeps |
| --- | --- | --- |
| `file`, frozen | a scanned policy, a signed contract, a statement PDF | a copy in the documents store at `path`, and its `sha256` |

- **Filing is file first, then the entry that names it. Removing is the entry first, then the file.** The order keeps a reference from pointing at nothing.

## Snapshots

A snapshot records a folded answer so it need not be recomputed. It carries `scope`, the question's meaning normalized so paraphrases land on one scope, a body holding the answer, and `read_upto`, the last `seq` it had read in each writer's stream:

```json
"scope":"family car service history",
"read_upto":{"desktop-7f3a9c":4127,"laptop-c91e02":88}
```

A snapshot is stale when any stream holds a record past its mark, or a stream it does not name holds any record, and those records are what a reader replays on top of it. A time is never the watermark; [the decision](decisions/sequence-watermark-for-snapshots.md) says why.
