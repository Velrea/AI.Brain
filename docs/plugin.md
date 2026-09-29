---
covers: [plugin/**]
---

# The plugin

The Brain is an MCP server. The plugin carries the server, a launcher, and skills.

- **The server runs over stdio.** The agent's host starts it for a session and stops it with the session.
- **A launcher prepares the machine on first run.** It builds a virtual environment, installs the pinned `mcp` and `duckdb` packages into it, and starts the server. Python is the machine's own.
- **The software and the data are separate.** The plugin is installed on each machine; the Brain is the data in the configured folders. A second machine pointed at the same synced folders reaches the same Brain as another writer.

## Configuration

Two folders, given to the server when it starts:

| Setting | Holds |
| --- | --- |
| Event store | the records |
| Documents store | the filed documents |

## Tools

| Tool | Does |
| --- | --- |
| `write` | records an entry and returns its id |
| `search` | finds entries by text, date, entity, and type, returning each hit's id, date, description, and a snippet, paged |
| `read` | returns full entries, as markdown, for a list of ids in one call |
| `store_document` | files a document into the documents store and returns its path and hash, for an entry to reference |

Each tool's description carries the rules it enforces, so an agent without the skills gets the same behavior.

## Skills

Skills keep only judgment; nothing mechanical stays in a skill.

- `journal`: listen, ask follow-up questions until the account is complete, check the newest similar entry and match its layout, then write.
- `query`: search, read, and fold into an answer, offering a snapshot when a fold was expensive.
- `intake`: read a document, store it, and write the one entry that carries its contents.
