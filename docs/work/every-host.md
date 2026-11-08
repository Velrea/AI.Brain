# Every host

The Brain installs as a plugin on every agent host that takes one, with nothing to set up at install: Claude Code, Codex, Cursor, and whichever comes next. Promoted from the idea [`every-host`](../ideas/every-host.md), which holds the design.

## Decided

- **Each install is its own machine**, sharing nothing with another install but the Brain folder.
- **The Brain folder is set in the first conversation** on every host, kept in the install's data folder. `configure` sets it, and calling it again changes it.
- **A Brain folder that does not exist is created only when the user says to.**
- **Filing moves into the server**, so no skill depends on a host filling in its text or giving the model a shell.
- **Installs on `main` are live**, so an existing Claude install carries its Brain folder over with nothing asked. The setting's declaration goes now. On its first start, the server reads the saved value from Claude Code's own settings and never writes them. It asks only when it finds none, or more than one that differ.
- **No index catch-up at startup.** The first read catches up, as every read does: under a second for a Brain of a few thousand entries built from empty.

## Suggested

- Filing removes an original only once its copy is in place, the tool is marked destructive, and paths are absolute, with a Git Bash path read as its Windows path.
- Try an install on Codex and Cursor before the manifests and the hook removal, since their behaviour is unconfirmed.

## Done when

- The server starts with no Brain folder configured, a Brain folder that is missing, or a failed check. Every tool answers with what is wrong and how to fix it, and `configure` and `status` work.
- An existing Claude install keeps its Brain folder, with nothing asked.
- Filing works through the server's tools on every host, and the document skill uses them.
- The manifests, skills' frontmatter, and marketplaces load on Claude Code, Codex, and Cursor, with no hook and no install-time setting, and a test keeps the manifests in step.
- The docs describe the plugin as built.
