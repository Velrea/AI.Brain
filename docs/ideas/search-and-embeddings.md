# Search and embeddings

Concerns reading.

Meaning-based search over the Brain, beside the full-text search the local index holds.

- **Vectors live in the local index**, beside the full-text index, and are searched there.
- **Embeddings are computed on the read side and kept outside the disposable index**, keyed by a hash of the text and the model, so rebuilding the index never recomputes one. One Brain keeps one embedding model, and it runs locally: nothing is sent off the machine.
- **Entities could be resolved by meaning** as well as by name and alias, if resolving by name leaves duplicates. Meaning complements spelling: a model is likely to link `meds` to `medication` and weak on shorthand such as `Dr. J`, which spelling already catches. Verify both on a local model before relying on either.

Open: which local embedding model.
