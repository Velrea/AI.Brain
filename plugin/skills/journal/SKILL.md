---
name: journal
description: "Writes a journal entry to the Brain, or corrects one, and decides unprompted whether an event that just surfaced deserves one."
when_to_use: "A request to journal, record, or write down an event, conversation, appointment, decision, or observation, or to correct something recorded. A life event the user mentions in passing, with no request behind it."
argument-hint: "[the event to record]"
---

You record what happened in the user's life as a journal entry: an account a reader who was not there can follow months later.

## Decide whether to record

A request is the decision. Unprompted, judge two things: is the user a party to the event or only an observer of it, and has it happened. How important it seems is not a test.

- **Record it** when the user was a party, it has happened, and the user said so.
- **Offer, and record on a yes,** when the user only observed it, when it has not happened yet, or when you found it rather than being told. An intention is an offer.
- **Stay silent** about the session's own work, and about anything that answers no question about the user's life.

## Get the whole account

Ask follow-up questions until the account is complete: who, what was said or decided, figures, dates, what happens next. An entry is permanent, so an unclear date, name, number, or outcome goes to the user before it is written; a guess becomes a permanent error. Stop asking once a reader could reconstruct the event from the entry alone.

## Find its subjects

Name the entities the entry is about: each specific person, thing, or topic that persists beyond this event, such as a doctor, a medication, a car, or a home, including those beyond the main subject, and the broad subject it falls under, such as `medication` for a change of dose, so a question about the whole subject finds it. Something mentioned only in passing stays in the body, and an occurrence such as an appointment is the entry itself, never an entity.

Pass every subject to `resolve` at once. Reuse an entity that matches, and when the entry names it a new way, restate it with `write_entity` adding that name as an alias, so it is found by it next time. Write a new entity only when nothing matches; when a match is plausible but uncertain, ask the user, since a wrong match merges two real things and a needless new one splits one.

## Match the layout

Search for the newest entry like this one, by its entities and `newest_first`, and read it. Where entries of this kind already have a layout, such as the same headings for each visit to a doctor, follow it, so entries of a kind read alike.

## Write it

Call `write_journal`:

- **event_date:** the day it happened, not the day it is recorded. One event per entry.
- **description:** one line someone can decide from without opening the entry, such as "Oil change at 48k, rear brakes flagged as worn", not "Oil change". A search returns only these lines, so the description decides whether an entry is read.
- **body:** Markdown, for a reader who was not there.
  - What happened, concretely: who said or did what. Not "talked about the car" but "the mechanic said the rear brakes have about 3 mm left".
  - Exact values: numbers, dates, amounts, names, and the terms used.
  - People by name, never only by pronoun.
  - Decisions marked "Decision:", action items with who committed to what by when, and open questions.
  - Only the last digits of an account, card, or government number, such as "card ending 1234".
- **entities:** the slugs resolved above.
- **source:** how it arrived, such as `voice` or `email`, when known.

A document the user hands over is filed through the `intake` skill, which writes its entry. An entry about a document already filed carries the document's contents, as close to all of them as is useful, and names it by the path and `sha256` it was filed with. A document that changes later is a new event: a new entry naming its new `sha256`, so the old entry's hash still says what the document was when it was written.

## Corrections and new information

A correction and new information are separate writes. Read the whole account against the entry it concerns, and tell the parts apart:

- **A correction** fixes what the entry recorded wrong: a fact, an amount, a name, a spelling, its date, its entities, or its description. It goes through `revise_journal` on that entry, with an amendment saying what was wrong and what is right. The body is never replaced; the amendment travels with it.
- **New information** about the same story, such as a later event, a next step, or a detail not known then, is a new chapter: a new entry on its own date, connected to the story by the entities it shares.

An account that carries both produces both: a revision holding only the correction, and a new entry holding the rest.
