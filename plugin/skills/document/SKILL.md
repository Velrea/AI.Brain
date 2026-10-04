---
name: document
description: "Files a document into the Brain and records it, and records changes to the documents already filed."
when_to_use: "The user hands over a file or a folder of files to file, save, archive, or put in the Brain, says a filed document has changed, or asks to check the filed documents."
argument-hint: "<file or folder> [what it is]"
---

File only when asked; never watch a folder.

## Script

`"${CLAUDE_PLUGIN_ROOT}/scripts/brain" run "${CLAUDE_SKILL_DIR}/scripts/documents.py" <command>`; from PowerShell or cmd, `scripts/brain.cmd`. Prints one JSON object, or an error.

- `list --brain "${user_config.brain_folder}" "<folder>"`: a folder's subfolders with their document counts, and its documents. Empty folder: the top.
- `store --brain "${user_config.brain_folder}" --data "${CLAUDE_PLUGIN_DATA}" "<file>" "<path>" [--move]`: files it, removes the original with `--move`, prints `path` and `sha256`. Refuses contents already recorded, a path holding other contents, and a file already in the Brain's documents.
- `check --brain "${user_config.brain_folder}" --data "${CLAUDE_PLUGIN_DATA}" "<path>"`: how the documents at a folder or one document, or every one when empty, differ from their entries, as `changed`, `moved`, `missing`, and `unrecorded`. Reads each document whole, so check no more than asked.

## Each document

1. Read it whole. If you can't, ask what it is. A pointer, a file whose contents only point to content kept elsewhere, is filed like any document: read that content through whatever this session can reach; if nothing can, ask what it holds.
2. Place it. `list` from the top; file beside similar documents without asking. Otherwise nest area, thing, kind, using only the levels that help, and offer two or three paths, recommended first, once per batch. Follow any existing pattern. Folders are lowercase words joined by hyphens; files are `YYYY-MM-DD-<what-it-is>.<ext>` by event date, or `<what-it-is>.<ext>`.
3. `store` it with `--move`. Already recorded: skip it and say where it is. Original not removed: carry on with the printed path and sha256, and say so.
4. Find its subjects (`search` by `names`, `types: ["entity"]`), then write:

```
type: document
version: 1
slug: <what it is; its date first if it records an event>
event_date: <the event's date, else the date it bears>
description: <one line: what it is and what about it matters>
body: <its contents, less boilerplate; a pointer's, what its content says>
links: <subjects>
details: {"path": "<from store>", "sha256": "<from store>", "address": "<a pointer only: where its content lives>"}
```

Write failed: write again; never file again.

Then hand the batch to `journal`.

## Web pages

A web page has no file: never file it. Hand what it says to `journal`, with `details: {"address": "<its address>"}`.

## Documents already filed

The user may edit, move, add, or delete files in the Brain's documents by hand. Handed a file already there, told one has changed, or asked to check the documents, `check` that document, its folder, or the top, and record what it reports:

- `changed`: read the document, and revise its entry with `details: {"sha256": "<new>"}` and a `body` saying what changed.
- `moved`: revise its entry with `details: {"path": "<to>"}`.
- `unrecorded`: write its entry as in step 4, with the printed path and sha256, and hand it to `journal`.
- `missing`: say so, and ask what became of it.
- Nothing reported: say it is recorded as it stands.

## Also

- A pointer whose content changed since it was recorded: revise its entry with a `body` saying what changed.
- Report each document's path, its entry's description, and any original left in place.
