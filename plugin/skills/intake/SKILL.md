---
name: intake
description: "Files a document into the Brain: finds where it belongs among the Brain's documents, moves it there, and writes the one journal entry that carries its contents."
when_to_use: "A file or folder of files handed over to put into the Brain, file, archive, save, or record, or a document to be dealt with. A web address handed over the same way."
argument-hint: "<file or folder to file> [what it is]"
---

You file a document into the Brain: it moves into the Brain's documents, and one journal entry records it and carries what it says. The entry is what a later search finds and a later answer draws on; the document is there to go back to.

File only when the user asks. A document named in passing is not that request, and you never watch a folder or start filing on your own.

## Read it

Read the whole document before anything else, with whatever this host offers for its kind of file. You need its contents for the entry, and its date and subject to choose where it goes. If you cannot read it, ask the user what it is rather than guessing.

## Choose where it goes

The documents folder is organized for the user to browse by hand, so its structure must make sense to a person looking for something. Browse it with `list_documents`, from the top down, and fit the document beside documents like it.

The structure grows as documents arrive, in three levels where they help:

1. **A life area**, such as `assets`, `employment`, `finance`, `health`, `identity`, `legal`, `pets`, `projects`, or `reference`.
2. **The specific thing**, such as a vehicle (`assets/blue-hatchback`), a home (`assets/lakeside-cottage`), a provider (`health/providers/dr-jekyll`), an institution, an employer, a pet, or a year for what comes yearly (`finance/tax/2025`).
3. **The kind of document**, such as `service`, `insurance`, `registration`, `purchase`, or `vet`.

Folders are lowercase words joined by hyphens. A file is named for the date of the event it records, then what it is, in the same style: `2026-09-14-oil-change-invoice.pdf`, with the visit's or the invoice's date, never the day it was filed. A document with no event of its own, such as a manual, keeps a plain descriptive name. Where the folders already in use follow a pattern of their own, follow it instead.

When a folder already holds documents like this one, file it there without asking. Otherwise ask before filing: offer two or three paths, your recommendation first, and let the user give another. Ask once for a batch, not per document.

## File it

Call `store_document` with `move: true`, so one copy remains and it is the filed one.

- **Refused as already filed:** an entry already names these contents. Skip this document, leave the original where it is, and tell the user where it was filed.
- **Filed, but the original could not be removed:** the error gives the path and `sha256`. Name the document by them, carry on, and tell the user the original is still there.

## Write the entry

Write one journal entry through `write_journal`, finding its subjects and writing its description the way the `journal` skill does, with these for a document:

- **event_date:** the date of the event the document records.
- **description:** what the document says that matters, such as "Oil change at 48k, rear brakes flagged as worn", not "Invoice".
- **body:** the document's contents, as close to all of them as is useful, in Markdown. Leave out what does not bear on it, such as boilerplate and copyright notices, and keep only the last digits of an account, card, or government number.
- **documents:** what `store_document` returned, exactly.
- **source:** how the document arrived, such as `email` or `scan`, when known.

If writing the entry fails after the document is filed, fix what the error names and write it again with what `store_document` returned. Never file the document again.

## A batch

A folder handed over at once is filed one document at a time, each into its own place. Documents about the same event, such as a visit's lab report and its bill, share one entry naming each of them; unrelated documents get entries of their own.

## A web address

A web page is never copied into the Brain. Offer to journal what it says instead, with its address in the body.

## Tell the user

Say where each document was filed, the description of the entry that records it, and any original still where it was.
