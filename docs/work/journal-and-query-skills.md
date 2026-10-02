# The journal and query skills

Capture and retrieval take judgment the tools cannot hold: what deserves an entry, what to ask first, how the body reads, and how entries fold into an answer. The skills keep that judgment and how to use the tools well; nothing a tool enforces stays in a skill.

The skills carry the long guidance, more than a tool's description should hold; [the MCP server](../mcp-server.md) carries the rules, and the skills call its tools.

## Decided

- `journal`: listen, ask follow-up questions until the account is complete, check the newest similar entry and match its layout, then write. It also records a life event unprompted when one surfaces in conversation.
- `query`: search, read, and fold entries into an answer, offering a snapshot when a fold was expensive.
- **Both skills teach the tools' use, not only the judgment.** Offered a way to search by subject with no guidance, two of three models ignored it and missed entries; one line of guidance made all three answer fully. `journal` identifies an entry's [entities](../core-module.md#entities) and resolves them before writing; `query` resolves the question's subjects first, then runs one search by those entities plus words for wording they might miss.
- **`journal` writes a description a reader can triage from** without opening the entry, such as "Oil change at 48k, rear brakes flagged as worn" rather than "Oil change". A search returns only lean hits, so the description decides whether an entry is read; it is written once, by a model looking at that entry alone.
- **`query` searches, then reads only the ids it picks.** It may search several times to build up the list. A search that finds more than the ceiling fails with how to refine it, and an answer drawing on everything about a subject covers every one of the event-date ranges the failure gives, folding as it reads rather than loading every body at once. That walk is an expensive fold, so it ends in an offered snapshot.

## Done when

- `journal` asks follow-up questions until the account is complete, matches the layout of the newest similar entry, and writes through `write_journal`.
- `query` searches, reads, and folds entries into an answer, and offers a snapshot when a fold was expensive.
- Neither skill does anything a tool already enforces.
