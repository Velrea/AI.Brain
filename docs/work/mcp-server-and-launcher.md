# The MCP server and the launcher

The MCP server is how an agent reaches the Brain. It imports [the core module](core-module.md) and wraps it: a separate thing beside the module, holding no logic about the data of its own. It carries the rules itself, so an agent without the skills gets the same behavior.

It comes right after the core module, with `write` and `store_document` first; `search` and `read` arrive with [reading](reading.md).

## Settled

- **The server runs over stdio.** The agent's host starts it for a session and stops it with the session.
- **A launcher prepares the machine on first run.** It builds a virtual environment, installs the pinned `mcp` and `duckdb` packages into it, and starts the server. Python is the machine's own.
- **The software and the data are separate.** The plugin is installed on each machine; the Brain is the data in the configured folders. A second machine pointed at the same synced folders reaches the same Brain as another writer.

Configuration is two folders, given to the server when it starts:

| Setting | Holds |
| --- | --- |
| Event store | the records |
| Documents store | the filed documents |

| Tool | Does |
| --- | --- |
| `write` | records an entry and returns its id |
| `search` | finds entries by text, event date, and type, returning each hit's id, event date, description, and a snippet, paged |
| `read` | returns full entries, as markdown, for a list of ids in one call |
| `store_document` | files a document into the documents store and returns its path and hash |

- **Each tool's description carries the rules it enforces.**
- **A filed document** is a copy of the file, kept in the documents store at its path, with its `sha256`.

## Done when

- On first run the launcher builds a virtual environment, installs the pinned `mcp` and `duckdb`, and starts the server.
- The server starts with the event store and documents store folders it is given.
- In a real agent session, `write` and `store_document` are callable and do what the table says.

## Open question

How an entry points at a filed document, now that the record carries no references. Filing was to be file first, then the entry that names it, so a pointer never points at nothing.
