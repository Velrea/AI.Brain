# Search and embeddings

Concerns [reading](../read-and-write.md).

Full-text and meaning-based search over the Brain.

- **Indexes live on DuckDB tables, not on views over files.** The full-text index is rebuilt whole when entries arrive; the vector index must fit in memory.
- **Embeddings are computed on the read side and stored** in an `embeddings/<writer>/` stream keyed by entry id and model, so no process or machine computes one twice. One Brain keeps one embedding model.
- **A shared read service** on `localhost`, started by the plugin on the first query and stopped when idle, replaces a DuckDB per session once full-text rebuilds or embedding loads become noticeable. Writes stay in each session's own process. DuckDB lets only one process open a database file for writing, which is why a persisted DuckDB file waits for this service.

Open: the embedding model. A local one is free and offline but slower and a download; an API is better but needs a key and costs a little.
