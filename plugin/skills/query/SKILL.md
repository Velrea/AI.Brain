---
name: query
description: "Answers a question from what the Brain recorded."
when_to_use: "The user asks about something they may have recorded: what happened, what was said or decided, or how something stands now; or asks to look something up in the Brain."
argument-hint: "<the question to answer>"
---

Answer only from the record and sources you can check, never from what seems likely.

## Find

- Find the subjects and the broad subject: `search` by `names`, `types: ["entity"]`.
- `search` by their slugs plus the question's words. Search again only for gaps.
- `read` only the ids you pick; long entries a few at a time.
- How something stands now: start from the latest snapshot linking its subjects whose scope fits (`types: ["snapshot"]`, `newest_first`). Fold in what was recorded after it, reaching back a few days.
- Past the ceiling and needing everything: search each range the error lists, folding as you go.

## Fold

- Event-date order; a later entry supersedes an earlier one.
- An entry stating a whole set restarts that set; when unsure, treat it as a change.
- A contradiction the order cannot settle: show both with dates, and ask.

## Beyond the Brain

Follow what the record points to, or what it lacks, to sources this session can reach. Send out only what the lookup needs.

## Answer

- Brief; say where more is.
- Cite entries by date and description; keep other sources apart.
- Nothing by subject, wording, or date: say the Brain does not record it.
- After an expensive fold: give the entry count and offer a snapshot; on yes, use `snapshot`.
