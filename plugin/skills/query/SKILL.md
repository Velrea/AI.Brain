---
name: query
description: "Answers a question about the user's own life from the Brain, folding the journal entries that bear on it into the answer."
when_to_use: "Any question about the user's own history, health, home, vehicles, finances, insurance, work, or the people around them; any request to search the Brain or the journal, look something up, recall what happened, or say how something stands now."
argument-hint: "<the question to answer>"
---

You answer a question about the user's life from what the Brain recorded, never from what seems likely.

## Search

1. **Resolve the question's subjects first.** Pass every person, thing, and topic it names to `resolve` at once. A broad question names a broad subject: "my medications" resolves to an entity such as `medication` that every medication entry names.
2. **Search once by those entities plus words** for wording they might miss: `search` with the entities' slugs and a pattern of the question's own terms. An entry is a hit when either finds it, so an entry whose entities were missed when it was written still turns up.
3. **Search again where the hits leave a gap**, by other words, other entities, or event dates, until the hits are the entries that bear on the question. Hits are lean, so judge them by their descriptions and snippets.
4. **Read only the ids you pick**, and long entries a handful at a time. `read` returns everything asked for, and a large result costs turns to page through and room to hold.

A search that finds more than the ceiling fails with how to refine it. Narrow it where the question allows. An answer that draws on everything about a subject covers every one of the event-date ranges the failure gives, folding as it reads rather than loading every body at once.

## Start from a snapshot

A question about how things stand now may already have a snapshot. Search for `types: ["snapshot"]` with the question's words, `newest_first`, and read the latest whose scope fits. Then search the same subjects with `recorded_after` a few days before the snapshot's `recorded_at`, to catch entries that synced late, and fold those into it.

## Fold

A single fact is answered from its entry. How something stands now, what a set holds, or how something changed is folded in event-date order, a later entry superseding an earlier one.

- An entry that states a whole set, such as every medication taken now, restarts the fold for that set; one that adds or removes a member does not. Unsure which it is, treat it as a change, since misreading it drops earlier facts.
- An entry comes with its revisions applied and its amendments under it; the amendments are corrections, and they hold.
- Where two entries contradict and their order does not settle it, do not guess: state the conflict, give both with their dates, and ask.

## Answer

Answer briefly: what it takes to answer the question, the details kept short, and where more is available, such as the visit's other findings or the full figures. The user asks again for more; do not synthesize everything you read. Say which entries the answer rests on, by date and description.

When searching by the subjects, by other wording, and across every date finds nothing, say the Brain does not record it. That is an answer.

When the fold was expensive, such as one that walked the ranges of a search past the ceiling or read many entries, say how many entries it took and offer to save it as a snapshot. On a yes, build the answer afresh from every matching entry and record it with `write_snapshot`, its scope put so paraphrases of the question land on it, such as "current medications".
