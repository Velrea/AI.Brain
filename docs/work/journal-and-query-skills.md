---
status: ready
claimed-by:
branch:
---

# The journal and query skills

The `journal` and `query` skills, as [`plugin.md`](../architecture/plugin.md) describes.

## Acceptance criteria

- `journal` asks follow-up questions until the account is complete, matches the layout of the newest similar entry, and writes through `write`.
- `query` searches, reads, and folds entries into an answer, and offers a snapshot when a fold was expensive.
- Neither skill does anything a tool already enforces.
