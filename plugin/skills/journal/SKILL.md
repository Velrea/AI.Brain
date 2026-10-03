---
name: journal
description: "Records what happened as a journal entry, or corrects one."
when_to_use: "The user asks to journal, record, note, or correct something, or mentions in passing something that has happened or is planned that they would want to recall later."
argument-hint: "[the event to record]"
---

Record what happened so a reader who was not there can follow it months later.

## Whether to record

A request decides it. Unprompted, record what the user took part in and has already happened. Offer, and record on a yes, what they only observed, what has not happened yet, or what you found rather than were told. Never record the session's own work.

## The account

Ask follow-up questions until the account is complete. Ask rather than guess at anything unclear: an entry is permanent.

Find every subject: each person, thing, or topic that outlasts the event, and the broad subject it falls under, so a question about the whole subject finds it. Search for them all at once by `names`, with `types` of `entity`. Link to each match; record a subject with no match, or a new name for a match, through `entity`. Ask about an uncertain match rather than merging two things or splitting one. Link as well to an earlier entry this one follows on from, and to the document entries of any documents it concerns.

Read the newest entry like this one and follow its layout.

## The entry

Record it with `write`:

- `type`: `journal`
- `version`: `1`
- `slug`: `<YYYY-MM-DD>-<a few words naming the event>`
- `event_date`: `<YYYY-MM-DD, the day it happened>`
- `description`: `<one line a reader can triage from without opening the entry: what happened and what about it matters, never only the kind of event>`
- `body`: `<Markdown: what happened, concretely, with every value exactly as given and everyone by name; what was decided, who committed to what by when, and what was left open>`
- `links`: `<the slugs of its subjects, documents, and any entry it follows on from>`
- `source`: `<how it arrived, in a word>`

One event per entry. Keep every link or reference the account gives to where more of it lives. Never write a secret in full; keep only enough of it to tell it apart. A slug already taken gets more words.

## Documents

`document` files each document and records it as an entry of its own, then hands them here. Write the entry recording what was captured: what the documents say, summarized, and what surrounds them, linking to each document entry's slug. The documents are the account, so ask only about what they leave unclear, and date the entry by the event they record, or else the day they were captured. Documents about one event share one entry.

## Corrections

Read the account against the entry it concerns. What the entry got wrong is a correction, a `write` revising that entry:

- `type`: `journal`
- `version`: `1`
- `entry`: `<the id of the entry it corrects>`
- `body`: `<an amendment saying what was wrong and what is right>`
- `description`, `event_date`, `links`: `<only those that change, each replacing the entry's>`

Anything the entry did not hold is new: a new entry on its own date, linking to the one it follows on from. An account with both gets both.
