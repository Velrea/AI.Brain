# Parquet compaction

Concerns [storage](../read-and-write.md).

Sealed files compact to ZSTD Parquet, about 3 times smaller than the JSONL, and move to any remote store, with a local cache of sealed files that queries run against.
