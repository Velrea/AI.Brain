---
name: query
description: "Answers a question about the user's life from the Brain."
when_to_use: "The user asks about their own past or present, what happened, or how something in their life stands now, or asks to look something up in the Brain."
argument-hint: "<the question to answer>"
---

Answer from what the Brain recorded, never from what seems likely.

## Find

Resolve the question's subjects, including the broad subject the question covers. Search by those slugs plus the question's words, then again only where the hits leave a gap. Read only the ids you pick, long entries a handful at a time.

For how something stands now, start from the latest snapshot whose scope fits.

When an answer needs everything about a subject and the search passes the ceiling, search each range the failure gives, folding as you read.

## Fold

Fold in event-date order, a later entry superseding an earlier one. An entry stating a whole set restarts the fold for that set; when unsure, treat it as a change. Where the order cannot settle a contradiction, show both entries with their dates and ask.

## Answer

Answer briefly, name the entries the answer rests on by date and description, and say where more is available. When nothing turns up by subject, by wording, or across dates, say the Brain does not record it.

After an expensive fold, say how many entries it took and offer a snapshot. On a yes, rebuild the answer from every matching entry and write it.
