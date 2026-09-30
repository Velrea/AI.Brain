# The MCP server and the launcher

The MCP server is how an agent reaches the Brain. It imports [the core module](core-module.md) and wraps it: a separate thing beside the module, holding no logic about the data of its own. It carries the rules itself, so an agent without the skills gets the same behavior.

It comes right after the core module, with `write` and `store_document` first; `search` and `read` arrive with [reading](reading.md).

## Settled

- **The server runs over stdio.** The agent's host starts it for a session and stops it with the session.
- **A launcher prepares the machine on first run.** It builds a virtual environment, installs the pinned `mcp` and `duckdb` packages into it, and starts the server. Python is the machine's own.
- **The software and the data are separate.** The plugin is installed on each machine; the Brain is the data in the configured folders. A second machine pointed at the same synced folders reaches the same Brain as another writer.
- **The server finds the machine's state folder when it starts** and hands it to the core module. It takes the first of these that is set: `BRAIN_STATE_DIR`, `CLAUDE_PLUGIN_DATA`, `PLUGIN_DATA`, `COPILOT_PLUGIN_DATA`, and otherwise a fixed folder for the user on the machine, such as `%LOCALAPPDATA%\AI.Brain`. Hosts name the plugin's data folder differently, and some give none. The plugin's server config sets `BRAIN_STATE_DIR` to `${CLAUDE_PLUGIN_DATA}`, for hosts that expand the variable in config but do not pass it on. A value still holding `${` was not expanded, and counts as unset. The server logs which folder it chose and why.
- **The state folder is never inside the synced folders or the plugin's install folder**, which is replaced on every update. Any other choice is safe: sessions that do not share a state folder write separate files and never touch each other's, so a host that gives each session a fresh folder costs only small files. Cowork is reported to do this, with a data folder per conversation; that is unconfirmed.

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
- The server takes its state folder in the order above, skipping an unexpanded `${...}`, and logs which it chose.
- In a real agent session, `write` and `store_document` are callable and do what the table says.

## Open question

How an entry points at a filed document, now that the record carries no references. Filing was to be file first, then the entry that names it, so a pointer never points at nothing.
