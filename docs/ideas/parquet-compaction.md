# Parquet compaction

Concerns storage.

Sealed files compact to ZSTD Parquet, about 3 times smaller than the JSONL, and move to any remote store, with a local cache of sealed files that queries run against.
