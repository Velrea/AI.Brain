# Reading

The read path: what happened, how things stand now, and what changed, fast enough to feel conversational.

It extends [the core module](core-module.md) with a reading module beside the write path, and adds `search` and `read` to [the MCP server](mcp-server-and-launcher.md).

## Settled

- **The reading module depends on the file format alone**, through the record's shape and the folders' layout in the core module's shared module, never on the writer's internals.
- **DuckDB reads the JSONL files in place**, across every file in `events/`, through views over the files that state their columns. There is no index and no second copy. DuckDB never writes the record.
- **Every file is read on every read.** A machine that has gone quiet can come back.
- **A line that is not valid JSON is skipped**, including a half-written last line.
- **A record whose `id` has already been read is skipped**, so a line copied into two files is returned once.
- **Order is `event_date`, not `recorded_at` or file position.** Records from different files interleave only by what they say.
- **Results come back lean and paged**: `search` returns each hit's id, event date, description, and a snippet; `read` returns full entries for a list of ids.
- **A snapshot records a folded answer** so it need not be recomputed. It carries `scope`, the question's meaning normalized so paraphrases land on one scope, a body holding the answer, and `read_upto`, the number of lines it had read in each file:

```json
"scope":"family car service history",
"read_upto":{"h-0199a8c4-….jsonl":10000,"h-0199f02e-….jsonl":88}
```

- **A snapshot is stale** when any file holds more lines than its mark, or a file it does not name exists, and the records past the marks are what a reader replays on top of it. A file holding fewer lines than its mark was truncated, and is reported. Neither a time nor an `id` is ever the watermark: either would miss a record that syncs late, which a line count catches past the mark in its own file. A whole file that never arrives goes unnoticed; that is left to the sync service and backups. A snapshot is written only at the user's word.

## Done when

- A half-written last line is skipped, not returned or reported as an error.
- `search` returns ids, event dates, descriptions, and snippets, paged, filterable by text, event date, and type.
- `read` returns full entries, as markdown, for a list of ids in a single call.
- A record that appears in two files is returned once.
- A snapshot is reported stale when any file holds more lines than its mark or a file it does not name exists, and the query returns the records past the marks.
- In a real agent session, `search` and `read` are callable through the server.

## Not settled

- Where a snapshot's `scope` and `read_upto` live, now that a record's fields are fixed and the body holds everything else.
