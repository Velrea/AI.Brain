---
name: intake
description: "Files a document into the Brain and records it."
when_to_use: "The user hands over a file or a folder of files to file, save, archive, or put in the Brain."
argument-hint: "<file or folder> [what it is]"
---

File only when asked; never watch a folder.

## Read it

Read the whole document first. If you cannot, ask the user what it is.

## Choose its place

The documents folder is for the user to browse by hand. Browse it with `list_documents`, and file beside documents like this one. Where there are none, nest by area, then the specific thing within it, then the kind of document, using only the levels that help. Folder names are lowercase words joined by hyphens. A file is named `YYYY-MM-DD-<what-it-is>.<ext>`, dated by the event it records, or `<what-it-is>.<ext>` when it records none. Where the folders follow a pattern of their own, follow it.

File without asking where documents like it are filed. Otherwise offer two or three paths, your recommendation first, once per batch.

## File it

Call `store_document` with `move: true`. Refused as already filed: skip it, and tell the user where it is. The original could not be removed: carry on with the path and `sha256` the error gives, and tell the user.

## Record it

Find its subjects by `names`, with `types` of `entity`, as `journal` does, then record it with `write`:

- `type`: `document`
- `version`: `1`
- `slug`: `<what it is, as a slug, beginning with its date when it records an event>`
- `event_date`: `<YYYY-MM-DD, the date of the event it records, or else the date it bears>`
- `description`: `<one line saying what it is and what about it matters>`
- `body`: `<its contents, less any boilerplate>`
- `links`: `<the slugs of its subjects>`
- `details`: `{"path": "<the path store_document returned>", "sha256": "<the sha256 store_document returned>"}`

If that fails, record it again; never file it again. When the document records an event, hand it to `journal`, which writes the event's entry linking to the document's slug.

A changed document is a `write` revising its entry, with `details` of `{"sha256": "<its new sha256>"}` and a `body` saying what changed, so the original's hash still says what it was.

A folder is filed and recorded one document at a time. A web page is never filed; offer to journal what it says, with its address.

Tell the user where each document went, its entry's description, and any original left in place.
