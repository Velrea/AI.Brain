---
name: document
description: "Files a document into the Brain and records it."
when_to_use: "The user hands over a file or a folder of files to file, save, archive, or put in the Brain."
argument-hint: "<file or folder> [what it is]"
---

File only when asked; never watch a folder.

A filed document is two things: the file, moved into the Brain folder's `documents/`, and an entry of type `document` that names the file and carries its contents. Entries about it link to the document entry's slug.

## The script

This skill's file work is done by its script, run through the plugin's launcher so it finds Python the same way on every machine:

`"${CLAUDE_PLUGIN_ROOT}/scripts/brain" run "${CLAUDE_SKILL_DIR}/scripts/documents.py" <command>`

From PowerShell or cmd, run `scripts/brain.cmd` beside it instead. Each command prints one JSON object, or a message saying what went wrong.

- `hash "<file>"`: the file's `sha256`.
- `list --brain "${user_config.brain_folder}" "<folder>"`: one folder of `documents/`, empty for the top: its folders with how many documents each holds, and its documents.
- `store --brain "${user_config.brain_folder}" "<file>" "<path>" --move`: files the file at that path inside `documents/`, removes the original once it is filed, and prints the `path` and `sha256`. A path that already holds other contents is refused; a file already in `documents/` is never moved.

## Read it

Read the whole document first. If you cannot, ask the user what it is.

## Filed already?

Hash it, and search for an entry with `types` of `document` and `details` of `{"sha256": "<its sha256>"}`. If one is found, skip it, and tell the user where it is filed.

## Choose its place

The documents folder is for the user to browse by hand. Browse it with `list`, and file beside documents like this one. Where there are none, nest by area, then the specific thing within it, then the kind of document, using only the levels that help. Folder names are lowercase words joined by hyphens. A file is named `YYYY-MM-DD-<what-it-is>.<ext>`, dated by the event it records, or `<what-it-is>.<ext>` when it records none. Where the folders follow a pattern of their own, follow it.

File without asking where documents like it are filed. Otherwise offer two or three paths, your recommendation first, once per batch.

## File and record it

File it with `store`. If the original could not be removed, carry on with the path and `sha256` the message gives, and tell the user.

Find its subjects by `names`, with `types` of `entity`, as `journal` does, then record it with `write`:

- `type`: `document`
- `version`: `1`
- `slug`: `<what it is, as a slug, beginning with its date when it records an event>`
- `event_date`: `<YYYY-MM-DD, the date of the event it records, or else the date it bears>`
- `description`: `<one line saying what it is and what about it matters>`
- `body`: `<its contents, less any boilerplate>`
- `links`: `<the slugs of its subjects>`
- `details`: `{"path": "<the path store printed>", "sha256": "<the sha256 store printed>"}`

If that fails, record it again; never file it again.

## Journal it

Once the documents are filed and recorded, hand them to `journal`, which writes the entry recording what was captured: what the documents say, summarized, and what surrounds them, linking to each document entry's slug. Documents about one event share one journal entry.

A folder is filed and recorded one document at a time, then journaled.

## A changed document

A changed document revises its entry with `write`, giving the entry's id, `details` of `{"sha256": "<its new sha256>"}`, and a `body` saying what changed, so the original's hash still says what it was.

## Not documents

A web page is never filed; offer to journal what it says, with its address.

Tell the user where each document went, its entry's description, and any original left in place.
