# Extension guide

Journal entries, entities, snapshots, and filed documents, with search and read over them, are the foundation anything else is built on. A use with behavior of its own, such as a ledger, a research topic, or a job search, records entries of its own. So a person builds what they need as a skill of their own over the Brain's tools, and a guide says how.

## Decided

- **The plugin ships no skill for a particular use.** A skill for one person's use is theirs to write and keep in their own setup.
- **An extension uses the MCP tools, never the core module's Python.** The core module lives in the plugin's install folder, which every update replaces, runs in the plugin's own environment, and writing through it skips the rules the tools carry.
- **An extension defines its type the way the plugin's own skills do**, through the generic calls, so it needs no change to the core module or the server.
- **The guide lives in the README, or in a document of its own for extending the Brain.**

## Suggested

- An extension's entries link to an entity for its subject, so a search by that entity's slug returns the whole set; a snapshot holds a running answer such as a balance, and its files are filed documents.

## Done when

- A person can read how to build a skill on the Brain: how to define its type, what to record as entries and entities, how to find and fold its records back, and what to leave alone.

## Depends on

- Unified entries
