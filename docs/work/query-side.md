---
status: ready
claimed-by:
branch:
---

# The query side

DuckDB views over the files, `search`, `read`, and snapshot staleness, as [`read-and-write.md`](../architecture/read-and-write.md) describes.

## Acceptance criteria

- Views over the files state their columns explicitly.
- A half-written last line is skipped, not returned or reported as an error.
- `search` returns ids, dates, descriptions, and snippets, paged, filterable by date, entity, and type.
- `read` returns full entries, as markdown, for a list of ids in a single call.
- A snapshot is reported stale when any stream holds a record past its mark or a stream it does not name holds any record, and the query returns those records.
