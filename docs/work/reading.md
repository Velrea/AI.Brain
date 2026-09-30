# Reading

The read path: what happened, how things stand now, and what changed, fast enough to feel conversational.

It extends [the core module](core-module.md) with a reading module beside the write path, and adds `search` and `read` to [the MCP server](mcp-server-and-launcher.md).

## Settled

- **The reading module depends on the file format alone**, through the record's shape and the folders' layout in the core module's shared module, never on the writer's internals.
- **DuckDB reads the JSONL files in place**, across every writer's folder, through views over the files that state their columns. There is no index and no second copy. DuckDB never writes the record.
- **Every writer folder is read on every read.** A writer that has gone quiet can come back.
- **A line that is not valid JSON is skipped**, including a half-written last line.
- **A duplicate `(writer, seq)` is flagged**, and a gap in a writer's `seq` is reported.
- **Order is `event_date`, not `recorded_at` or file position.** Streams from different writers interleave only by what the records say.
- **Results come back lean and paged**: `search` returns each hit's id, event date, description, and a snippet; `read` returns full entries for a list of ids.
- **A snapshot records a folded answer** so it need not be recomputed. It carries `scope`, the question's meaning normalized so paraphrases land on one scope, a body holding the answer, and `read_upto`, the last `seq` it had read in each writer's stream:

```json
"scope":"family car service history",
"read_upto":{"desktop-7f3a9c":4127,"laptop-c91e02":88}
```

- **A snapshot is stale** when any stream holds a record past its mark, or a stream it does not name holds any record, and those records are what a reader replays on top of it. A time is never the watermark; [the decision](../decisions/sequence-watermark-for-snapshots.md) says why. A snapshot is written only at the user's word.

## Done when

- A half-written last line is skipped, not returned or reported as an error.
- `search` returns ids, event dates, descriptions, and snippets, paged, filterable by text, event date, and type.
- `read` returns full entries, as markdown, for a list of ids in a single call.
- A snapshot is reported stale when any stream holds a record past its mark or a stream it does not name holds any record, and the query returns those records.
- In a real agent session, `search` and `read` are callable through the server.

## Not settled

- Everything here that names a writer's folder, a writer's stream, or `seq` rests on the per-machine layout and the `writer` and `seq` fields, which [the core module](core-module.md#not-settled) has not settled.
- Where a snapshot's `scope` and `read_upto` live, now that a record's fields are fixed and the body holds everything else, and what `read_upto` marks if `writer` and `seq` go.
