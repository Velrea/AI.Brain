---
status: ready
claimed-by:
branch:
---

# The tools and the launcher

The four tools and the launcher, as [`plugin.md`](../architecture/plugin.md) describes, and the plugin working in a real session.

## Acceptance criteria

- On first run the launcher builds a virtual environment, installs the pinned `mcp` and `duckdb`, and starts the server.
- The server starts with the event store and documents store folders it is given.
- In a real agent session, `write`, `search`, `read`, and `store_document` are callable and do what the tools table says.
