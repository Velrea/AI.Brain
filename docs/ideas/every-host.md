# Every host

Concerns installing, the MCP server, and the skills.

The Brain installs as a plugin on every agent host that takes one: Claude Code, Codex, and Cursor, each as CLI and desktop app, and whichever comes next. It installs with nothing to fiddle with, and each host's install has its own Brain folder setting.

## What carries over and what does not

| Part | Elsewhere |
| --- | --- |
| The MCP server, the core module, the launcher | Carries over: a stdio server any MCP host starts. |
| The skills' text | Carries over: every host reads `SKILL.md`. |
| The SessionStart hook | Optional already: it only builds the environment early, and the launcher builds it anyway before it starts the server. It is given no Brain folder, so it checks only that the data folder is outside the install folder, and it builds no index; every read catches the index up itself. |
| `userConfig.brain_folder` | Claude only. The shared format has no user settings; Cursor has its own `variables`; Codex has none found. |
| `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_SKILL_DIR}`, `${CLAUDE_PLUGIN_DATA}`, `${user_config.brain_folder}` in the document skill | Claude only. No other host is documented to fill in a skill's text. |
| `when_to_use` and `argument-hint` in skill frontmatter | Claude only, and outside the Agent Skills spec, whose reference validator rejects them. |

## The Brain folder

**Each host is configured on its own.** Every host's install of the plugin has its own Brain folder setting, and nothing checks one host's against another's. Point two hosts at the same folder and they share one Brain; point them at different folders and they keep two. Each host starts its own server, as each session does today.

**It is set the first way that applies:**

1. **At install, where the host asks.** Claude asks for `brain_folder` when the plugin is enabled, and Cursor for its `brain_folder` variable; each reaches the server as `BRAIN_DIR`, as today.
2. **In the first conversation, where the host asks nothing**, as Codex does. The server starts unconfigured: every tool answers that the Brain is not set up, and to ask the user for its folder. The `configure` tool takes the folder and saves it for that host, in `settings.json` in the data folder, under the host's name. Each host's server config names its host in `BRAIN_HOST`, so a second host on the machine is never configured by the first's answer. Asked again, `configure` changes it.

**A folder that does not exist is never created unasked.** A sync folder that is not mounted must not quietly become a new, empty Brain, as `brain_dir` requires today. The server still starts, and every tool answers that the Brain folder does not exist, naming it, and to ask the user whether to create it. Told yes, the model calls `configure` with `create`, which creates the folder and carries on there. Told no, it stops: it says the Brain cannot be used until the folder exists or another is configured, and does nothing more with it.

## The data folder

**One per machine, shared by every host's server.** The fixed per-user folder `folders.py` already falls back to: `%LOCALAPPDATA%\AI.Brain` on Windows, `~/Library/Application Support/AI.Brain` on macOS, and `$XDG_DATA_HOME/ai-brain`, by default `~/.local/share/ai-brain`, elsewhere. It holds the settings file, the virtual environment, and, for each Brain, the lock, the current file, and the index, which `folders.py` already keeps apart by a hash of the Brain folder's path.

- **The hosts' own data folders are no longer used.** `CLAUDE_PLUGIN_DATA`, `PLUGIN_DATA`, and `COPILOT_PLUGIN_DATA` each name a folder for one host, so three hosts pointed at one Brain would keep three indexes and three active event files. `BRAIN_DATA_DIR` stays, set by hand or by tests, never by a manifest.
- **Hosts pointed at the same Brain share its lock, current file, and index**, as sessions of one host share them today, so the machine keeps exactly one active file for each Brain.
- **Each version of the pins gets its own environment**, in a folder named by a hash of `requirements.txt`, so hosts running different plugin versions do not rebuild each other's. The launcher removes an environment no start has used for 30 days, never the index.
- **Existing installs move on their own.** The first start after the change uses the shared folder: its index is built from the files, and the machine starts a new active file. The old one is left as it is; only this machine ever wrote it. Nothing in the old folder is deleted.

## Filing moves into the server

The document skill's script needs the Brain folder and the data folder, which only Claude fills into a skill's text. Filing becomes the server's, where both are already known:

| Tool | Does |
| --- | --- |
| `list_documents` | a folder's subfolders with their document counts, and its documents |
| `store_document` | files a document, moving the original when asked, and returns its path and sha256 |
| `check_documents` | how the documents at a path differ from their entries |

- **The code moves to the core module** as `brain/documents.py`, standard library only, from `skills/document/scripts/documents.py`; its tests follow it. The server's tools call it as they call `Writer` and `Reader`.
- **The skill keeps the judgment**: where a document belongs, what its entry says, and what to do with what `check_documents` reports.
- **The rule changes.** Work that touches the Brain's files is the server's; what to record, and how, is the skills'. A skill script can rely on no host filling in its text, so `skills.md` no longer offers one as the way to reach the Brain.

## Setting up, checked at every start

The server checks everything as it starts, on every host, whether or not a hook ran: Python 3.11 or later, the environment, the Brain folder and that it exists, and that the data folder is outside the Brain folder and the install folder. It then catches up the index in the background, so the first question is answered from a current index.

- **A failed check does not stop the server.** Every tool answers with what failed and how to fix it, so the user hears it in the conversation instead of finding the tools missing.
- **`status`** reports the Brain folder and where it was set, the data folder, the Python and the pins, and how far the index has caught up. It is read-only.
- **The hook stays** where a host runs one, to build the environment before the host's shorter wait for a server to start.
- **Python 3.11 or later stays a requirement.** The launch scripts' message names it when none is found.

## Packaging

One `plugin/` folder carries every host's manifest. Each host reads its own and ignores the rest.

| File | Read by | Holds |
| --- | --- | --- |
| `plugin.json`, `mcp.json` | hosts of the Agent Plugins 1.0 format | the name and metadata; the server as `"type": "stdio", "command": "./scripts/brain"`, with `BRAIN_HOST` `agent-plugins` |
| `.claude-plugin/plugin.json`, `.mcp.json`, `hooks/hooks.json` | Claude Code | as today, less `BRAIN_DATA_DIR`, with `BRAIN_HOST` `claude`; `brain_folder` stays as the install-time question |
| `.cursor-plugin/plugin.json` | Cursor | the `brain_folder` variable, the server inline with `BRAIN_DIR` from it and `BRAIN_HOST` `cursor`, the `sessionStart` hook by `${CURSOR_PLUGIN_ROOT}` |
| `.codex-plugin/plugin.json` | Codex | the skills, the server with `BRAIN_HOST` `codex`, and the SessionStart hook |
| `skills/` | every host | as today, frontmatter limited to the Agent Skills spec's fields, with `when_to_use` folded into `description` |

- **Marketplaces** for each host sit at the repository root, as `.claude-plugin/marketplace.json` does: `.cursor-plugin/marketplace.json` and `.agents/plugins/marketplace.json` for Codex. Each entry carries only the name and the source.
- **A test keeps the manifests in step**: every one names the plugin `brain`, the same skills, and the same launcher, each names a different `BRAIN_HOST`, and none sets the data folder.
- **Any other MCP host** runs `scripts/brain`, or `scripts/brain.cmd` on Windows, from a clone; it is given `BRAIN_DIR`, or asks in the first conversation.

## Installing

| Host | Installs from | Brain folder |
| --- | --- | --- |
| Claude Code, CLI and desktop | this repository's marketplace, as today | asked at install |
| Cursor, editor and CLI | the Cursor marketplace, or this repository as a team marketplace | asked at install |
| Codex, CLI, desktop, and IDE | this repository's marketplace | asked in the first conversation |
| Any other | its Agent Plugins support, or one MCP entry | asked in the first conversation |

## To verify on each host before relying on it

Each of these is unconfirmed from documentation and needs an install on a real machine:

- **Cursor** passes a plugin `variable` into the server's `env`. Its HubSpot plugin uses variables only in `auth`.
- **Cursor** loads `.cursor-plugin/` alone when the root `plugin.json` is beside it, rather than both, which would start the server twice.
- **Codex** runs the `.codex-plugin/` hooks with a root `plugin.json` present. A Codex issue reports that the root manifest silently disables them; if it still does, the hook goes under `extensions` in the root manifest, or is dropped for Codex.
- **Codex** waits long enough for a first start that installs the environment, and its review of bundled hooks asks once, not every session.
- **Claude Code** ignores the root `plugin.json` and `mcp.json`.
- **Every host on Windows** runs `brain.cmd` for the command `./scripts/brain`.
- **Every host** loads a skill whose `description` carries what `when_to_use` said, and picks it as reliably.
- **Hosts that run plugins in a sandbox**, such as Cowork, keep the fixed per-user folder between sessions. Where they do not, the server falls back to the host's own data folder, at the cost of a fresh environment and active file per session.

## Order of work

1. `configure` and its settings file, `status`, and the shared data folder, with tests.
2. Filing into the server and the core module, with the document skill rewritten around it.
3. The manifests, the skills' frontmatter, the marketplaces, the consistency test, and the docs: `mcp-server.md`, `skills.md`, `core-module.md`, `development.md`, and the README's installing section.
4. An install on each host, working through the list above.
