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

The documents folder is for the user to browse by hand. Browse it with `list_documents`, and file beside documents like this one. Where there are none, nest by life area, then the specific thing within it, then the kind of document, using only the levels that help. Folder names are lowercase words joined by hyphens. A file is named `YYYY-MM-DD-<what-it-is>.<ext>`, dated by the event it records, or `<what-it-is>.<ext>` when it records none. Where the folders follow a pattern of their own, follow it.

File without asking where documents like it are filed. Otherwise offer two or three paths, your recommendation first, once per batch.

## File and record it

Call `store_document` with `move: true`. Refused as already filed: skip it, and tell the user where it is. The original could not be removed: carry on with the path and `sha256` the error gives, and tell the user.

Then record it through `journal`, naming it as `store_document` returned it. If that fails, record it again; never file it again.

A folder is filed one document at a time, then recorded through `journal`. A web page is never filed; offer to journal what it says, with its address.

Tell the user where each document went, its entry's description, and any original left in place.
