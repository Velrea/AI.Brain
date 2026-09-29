---
status: ready
claimed-by:
branch:
---

# The log

The write path: writer id, file lock, append, roll, `seq`, and torn-line handling, as [`data-format.md`](../data-format.md) and [`read-and-write.md`](../read-and-write.md) describe.

## Acceptance criteria

- Concurrent writers on one machine each append whole lines, and no `seq` repeats.
- A stream whose last line is torn gets that line ended with a newline before the next append, and the next `seq` follows the last valid line.
- A file that passes the roll size is sealed, the next numbered file opens, and `seq` carries on across the two.
- A writer id is generated once and reused; one whose `writer.json` names a different machine is replaced with a fresh one.

## Open question

Whether Google Drive for Desktop holds a file open while uploading, which would make an append retry, and whether it writes a downloaded file in place or replaces it whole, which decides what a reader sees mid-download. A script appending every 100 ms while a second machine reads the synced copy settles both.
