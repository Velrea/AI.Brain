# Entity audit

Concerns entities, writing, and reading.

- **An audit consolidates entities later**, a dreaming pass that looks through them for duplicates, such as `meds` beside `medication`, and merges them.
- **A command lists the entities in use**, with how many entries name each, for a query that starts by surveying the subjects, and for the audit.
- **Writing held up in an experiment.** Given about 1,000 existing subjects and twelve new entries worded loosely ("Dr. J doubled my Zorblax"), three models put a broad subject such as `medication` on every entry that needed it, mapped nicknames and shorthand such as "Dr. J" to the existing `dr-jekyll`, and invented no duplicates; their new subjects were for things the vocabulary lacked. They sometimes left out a broad one such as `health`. That run loaded the whole vocabulary, about 8,000 tokens per write, which resolving now narrows. It was a single run over generated data, so it shows the direction, not settled numbers.

- **A merge rewrites nothing**, through the repairs the local index applies. The model decides that two entities are one; one call, such as `merge_entity(old, into)`, does the writing: it restates the survivor with the old slug and names as aliases, repairs each entry naming the old slug to name the survivor, and last retires the old entity with a repair. Every repair states the final answer, so no chain of merges forms. A crash midway leaves the old entity findable, and running the call again repairs only the entries still naming it. An entry naming the old slug that syncs in later is caught by the next audit.
- **A retired slug counts as unrecorded** when a journal entry names it, and the refusal names the survivor.
