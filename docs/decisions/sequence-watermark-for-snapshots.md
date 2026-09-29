# A sequence watermark for snapshots

A snapshot marks what it has read with `read_upto`: the last `seq` it read in each writer's stream. It is stale when any stream holds a record past its mark, or a stream it does not name holds any record.

## Alternative

A time as the watermark: a snapshot covers every record recorded before the moment it was computed.

## Why

A time misses records that arrive late. An entry one machine records offline at 10:00 and a sync delivers at 10:30 would sort before a snapshot computed elsewhere at 10:15, and be skipped forever. A per-writer `seq` catches it, because the entry still sits past the snapshot's mark in its own stream.

Shaped [`data-format.md`](../data-format.md#snapshots).
