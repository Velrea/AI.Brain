# The tools and the launcher

The MCP server is how an agent reaches the Brain. It carries the rules itself, so an agent without the skills gets the same behavior.

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
| `search` | finds entries by text, date, entity, and type, returning each hit's id, date, description, and a snippet, paged |
| `read` | returns full entries, as markdown, for a list of ids in one call |
| `store_document` | files a document into the documents store and returns its path and hash, for an entry to reference |

- **Each tool's description carries the rules it enforces.**
- **A file reference** keeps a copy of the file in the documents store at `path`, and its `sha256`. Filing is file first, then the entry that names it, so a reference never points at nothing.

## Done when

- On first run the launcher builds a virtual environment, installs the pinned `mcp` and `duckdb`, and starts the server.
- The server starts with the event store and documents store folders it is given.
- In a real agent session, `write`, `search`, `read`, and `store_document` are callable and do what the table says.
