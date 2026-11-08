# Every host

Concerns installing, the MCP server, and the skills.

The Brain installs as a plugin on every agent host that takes one: Claude Code, Codex, and Cursor, each as CLI and desktop app, and whichever comes next. It installs with nothing to fiddle with. Each install is its own: it shares nothing with another install but the Brain folder it is pointed at.

## What carries over and what does not

| Part | Elsewhere |
| --- | --- |
| The MCP server, the core module, the launcher | Carries over: a stdio server any MCP host starts. |
| The skills' text | Carries over: every host reads `SKILL.md`. |
| The SessionStart hook | Goes. It only builds the environment early, which the launcher does anyway before it starts the server, and hosts run hooks differently or ask the user to trust each one. |
| `userConfig.brain_folder` | Goes. Claude only; the shared format has no user settings. The folder is set in the first conversation instead, on every host, and an existing Claude install's is carried over. |
| `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_SKILL_DIR}`, `${CLAUDE_PLUGIN_DATA}`, `${user_config.brain_folder}` in the document skill | Go. Claude only: no other host is documented to fill in a skill's text. Filing moves into the server, below, so no skill names a path. |
| `when_to_use` and `argument-hint` in skill frontmatter | Go. Claude only, and outside the Agent Skills spec, whose reference validator rejects them; what they say moves into `description`. |

## Each install is its own machine

**An install shares nothing with another but the Brain folder.** Each keeps its own data folder, the one its host gives it, holding its own settings, environment, lock, current file, and index. Claude and Codex installed on one machine and pointed at one Brain behave exactly as two machines sharing that Brain through a sync service: each appends to its own active file and rolls it on its own, and neither ever touches the other's files. An install on a second machine is no different.

**The data folder is the host's.** The first of `BRAIN_DATA_DIR`, `CLAUDE_PLUGIN_DATA`, `PLUGIN_DATA`, and `COPILOT_PLUGIN_DATA` that is set, as `folders.py` finds it today. Claude's server config sets `BRAIN_DATA_DIR` to `${CLAUDE_PLUGIN_DATA}`, as today; a host of the Agent Plugins format must give its server `PLUGIN_DATA`, a folder for that install that survives updates. A host that gives none falls back to the fixed per-user folder `folders.py` uses today. The data folder is never inside the Brain folder or the install folder, which is replaced on every update.

**Nothing in the data folder changes.** The lock, the current file, and the index stay as `core-module.md` describes them, so an existing install keeps its index and its active file.

## The Brain folder

**One setting, in the install's data folder.** `settings.json` there holds `brain_folder`. The server reads it as it starts. `BRAIN_DIR`, when set, still overrides it, for tests and for a host started by hand.

**It is set in the first conversation.** An install with no setting starts unconfigured: every tool answers that the Brain is not set up, and to ask the user for its folder. The `configure` tool takes the folder and writes `settings.json`. Called again, it changes the folder.

**A folder that does not exist is never created unasked.** A sync folder that is not mounted must not quietly become a new, empty Brain, as `brain_dir` requires today. The server still starts, and every tool answers that the Brain folder does not exist, naming it, and to ask the user whether to create it. Told yes, the model calls `configure` with `create`, which creates the folder and carries on there. Told no, it stops: it says the Brain cannot be used until the folder exists or another is configured, and does nothing more with it.

**An existing Claude install carries its folder over.** Claude Code keeps the value of `userConfig.brain_folder` in its own `settings.json`, under `pluginConfigs`, keyed by the plugin and its marketplace. As the server starts with no `settings.json` of its own and `CLAUDE_PLUGIN_DATA` set, it reads Claude's `settings.json`, in `CLAUDE_CONFIG_DIR` or else `~/.claude`. Exactly one `brain_folder` under a key for the plugin `brain` is written to the server's `settings.json`, with nothing asked. None, several that differ, or a file it cannot read, and the user is asked. Claude's file is only read, never written: Claude Code rewrites it itself, and once the setting is no longer declared, nothing reads the value left there. The next release drops this step, by when existing installs have updated.

## Filing moves into the server

The document skill's script needs the Brain folder and the data folder, and it runs in the model's shell. Only Claude fills a skill's text, and not even Claude can fill the Brain folder once it lives in the server's `settings.json`. A host may also give the model no shell, or one sandboxed from writing outside its project. Filing becomes the server's, where both folders are already known and no shell is needed:

| Tool | Does |
| --- | --- |
| `list_documents` | a folder's subfolders with their document counts, and its documents |
| `store_document` | files a document, moving the original when asked, and returns its path and sha256 |
| `check_documents` | how the documents at a path differ from their entries |

- **The code moves to the core module** as `brain/documents.py`, standard library only, from `skills/document/scripts/documents.py`; its tests follow it. The server's tools call it as they call `Writer` and `Reader`, handing it both folders, so it no longer imports `server/folders.py`.
- **Moving removes only what was filed.** A host can check each shell command before it runs; a tool may be allowed once and never checked again, and a document being filed can carry text telling the model to file others. So `store_document` keeps the script's order, removing the original only once its copy is in place in the Brain, and is marked destructive, for a host that asks before a destructive tool. At worst a file ends up in the Brain, never lost.
- **Paths are absolute.** The server's working folder is not the model's, so a relative path is refused, with how to give it whole. On Windows, a path as Git Bash writes it, `/d/...`, is read as `D:\...`: a shell converted it for the script, and nothing converts it in a tool call.
- **The skill keeps the judgment**: where a document belongs, what its entry says, and what to do with what `check_documents` reports.
- **The rule changes.** Work that touches the Brain's files is the server's; what to record, and how, is the skills'. A skill script can rely on no host filling in its text, so `skills.md` no longer offers one as the way to reach the Brain, and the launcher's `run`, which only skill scripts used, goes.

## Checked at every start

With no hook, the server checks everything as it starts: Python 3.11 or later, the environment, the Brain folder and that it exists, and that the data folder is outside the Brain folder and the install folder. The index catches up on the first read, as on every read: under a second for a Brain of a few thousand entries built from empty, and next to nothing when little is new.

- **A failed check does not stop the server.** Every tool answers with what failed and how to fix it, so the user hears it in the conversation instead of finding the tools missing.
- **`status`** reports the Brain folder, the data folder, and the Python and the pins. It is read-only.
- **The first start is the slow one.** Building the environment takes about 20 seconds while the host waits for the server. A host that stops waiting first costs that one session its tools; the build finishes, and the next session starts in about a second.
- **Python 3.11 or later stays a requirement.** The launch scripts' message names it when none is found.

## Packaging

One `plugin/` folder carries two manifests. Each host reads its own and ignores the other.

| Files | Read by | Hold |
| --- | --- | --- |
| `plugin.json`, `mcp.json` | Codex, Cursor, and every other host of the Agent Plugins 1.0 format | the name and metadata; the server as `"type": "stdio", "command": "./scripts/brain"` |
| `.claude-plugin/plugin.json`, `.mcp.json` | Claude Code | as today, less `userConfig` and `BRAIN_DIR` |
| `skills/` | every host | the skills, with frontmatter limited to the Agent Skills spec's fields |

- **No hooks, no host-specific settings**, so neither manifest names anything an install sets.
- **Marketplaces** for each host sit at the repository root, as `.claude-plugin/marketplace.json` does: `.cursor-plugin/marketplace.json` for Cursor and `.agents/plugins/marketplace.json` for Codex. Each entry carries only the name and the source.
- **A test keeps the manifests in step**: both name the plugin `brain`, the same launcher, and no setting.
- **Any other MCP host** runs `scripts/brain`, or `scripts/brain.cmd` on Windows, from a clone, and asks for the folder in the first conversation.

## Installing

| Host | Installs from | Brain folder |
| --- | --- | --- |
| Claude Code, CLI and desktop | this repository's marketplace, as today | asked in the first conversation |
| Cursor, editor and CLI | the Cursor marketplace, or this repository as a team marketplace | asked in the first conversation |
| Codex, CLI, desktop, and IDE | this repository's marketplace | asked in the first conversation |
| Any other | its Agent Plugins support, or one MCP entry | asked in the first conversation |

## To verify on each host before relying on it

Each of these is unconfirmed from documentation and needs an install on a real machine:

- **Cursor** gives its server `PLUGIN_DATA`. Its docs say it does not fill `${PLUGIN_DATA}` into `mcp.json`, which says nothing of the server's environment. If it gives none, two Cursor installs on one machine would share the fallback folder; that is safe, as sessions sharing one are, but they would no longer be separate machines.
- **Codex** gives its server `PLUGIN_DATA`, as it documents for hooks.
- **Cursor and Codex** list a plugin of the Agent Plugins format in their marketplaces with no manifest of their own.
- **Every host** waits long enough for a first start that builds the environment, and for a tool call that files or checks a large document.
- **Every host** runs the server where the model's file tools look, so a path the user names is one the server can open.
- **Claude Code** ignores the root `plugin.json` and `mcp.json`.
- **Claude Code** keeps a saved `brain_folder` in its `settings.json` when an update stops declaring it, at least until the server's first start after the update.
- **Every host on Windows** runs `brain.cmd` for the command `./scripts/brain`.
- **Every host** loads a skill whose `description` carries what `when_to_use` said, and picks it as reliably.

## Order of work

1. `settings.json`, `configure`, `status`, and carrying an existing Claude install's folder over, with tests.
2. Filing into the server and the core module, with the document skill rewritten around it.
3. The manifests, the skills' frontmatter, the marketplaces, the consistency test, removing the hook and `userConfig`, and the docs: `mcp-server.md`, `skills.md`, `core-module.md`, `development.md`, and the README's installing section.
4. An install on each host, working through the list above.
5. In the release after, removing the step that carries an existing Claude install's folder over.
