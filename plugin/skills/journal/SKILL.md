---
name: journal
description: "Records an event in the user's life as a journal entry, or corrects one."
when_to_use: "The user asks to journal, record, note, or correct something about their life, or mentions in passing something in their life that has happened or is planned."
argument-hint: "[the event to record]"
---

Record what happened so a reader who was not there can follow it months later.

## Whether to record

A request decides it. Unprompted, record what the user took part in and has already happened. Offer, and record on a yes, what they only observed, what has not happened yet, or what you found rather than were told. Never record the session's own work.

## The account

Ask follow-up questions until the account is complete. Ask rather than guess an unclear date, name, figure, or outcome: an entry is permanent.

Resolve every subject: each person, thing, or topic that outlasts the event, and the broad subject it falls under, so a question about the whole subject finds it. Add a new name for a match as an alias with `write_entity`. Ask about an uncertain match rather than merging two things or splitting one.

Read the newest entry like this one and follow its layout.

## The entry

- Date it the day it happened, one event per entry.
- In the body: who said or did what, with exact numbers, dates, amounts, and names; people by name, not pronoun; decisions, action items with who and by when, and open questions.
- Only the last digits of an account, card, or government number.

## A document

`intake` files a document, then records it here. The document is the account: ask only about what it leaves unclear. Date the entry by the event it records, carry the document's contents in the body less any boilerplate, and name it as `store_document` returned it. Documents about one event share an entry. A changed document is a new entry naming its new `sha256`.

## Corrections

Read the account against the entry it concerns. What the entry got wrong is a correction: `revise_journal` on that entry, with an amendment saying what is right. Anything the entry did not hold is new: a new entry on its own date, sharing the story's entities. An account with both gets both.
