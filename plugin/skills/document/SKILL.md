---
name: document
description: "Files a document into the Brain and records it."
when_to_use: "The user hands over a file or a folder of files to file, save, archive, or put in the Brain."
argument-hint: "<file or folder> [what it is]"
---

File only when asked; never watch a folder.

## Script

`"${CLAUDE_PLUGIN_ROOT}/scripts/brain" run "${CLAUDE_SKILL_DIR}/scripts/documents.py" <command>`; from PowerShell or cmd, `scripts/brain.cmd`. Prints one JSON object, or an error.

- `list --brain "${user_config.brain_folder}" "<folder>"`: a folder's subfolders with their document counts, and its documents. Empty folder: the top.
- `store --brain "${user_config.brain_folder}" --data "${CLAUDE_PLUGIN_DATA}" "<file>" "<path>" --move`: files it, removes the original, prints `path` and `sha256`. Refuses contents already recorded, and a path holding other contents.

## Each document

1. Read it whole. If you can't, ask what it is.
2. Place it. `list` from the top; file beside similar documents without asking. Otherwise nest area, thing, kind, using only the levels that help, and offer two or three paths, recommended first, once per batch. Follow any existing pattern. Folders are lowercase words joined by hyphens; files are `YYYY-MM-DD-<what-it-is>.<ext>` by event date, or `<what-it-is>.<ext>`.
3. `store` it. Already recorded: skip it and say where it is. Original not removed: carry on with the printed path and sha256, and say so.
4. Find its subjects (`search` by `names`, `types: ["entity"]`), then write:

```
type: document
version: 1
slug: <what it is; its date first if it records an event>
event_date: <the event's date, else the date it bears>
description: <one line: what it is and what about it matters>
body: <its contents, less boilerplate>
links: <subjects>
details: {"path": "<from store>", "sha256": "<from store>"}
```

Write failed: write again; never file again.

Then hand the batch to `journal`.

## Also

- Changed document: revise its entry with `details: {"sha256": "<new>"}` and a `body` saying what changed.
- Web page: never file; offer to journal what it says, with its address.
- Report each document's path, its entry's description, and any original left in place.
