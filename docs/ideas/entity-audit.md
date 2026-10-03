# Entity audit

Concerns entities, writing, and reading.

- **An audit consolidates entities later**, a dreaming pass that looks through them for duplicates, such as `meds` beside `medication`, and merges them.
- **A command lists the entities in use**, with how many entries name each, for a query that starts by surveying the subjects, and for the audit.
- **Writing held up in an experiment.** Given about 1,000 existing subjects and twelve new entries worded loosely ("Dr. J doubled my Zorblax"), three models put a broad subject such as `medication` on every entry that needed it, mapped nicknames and shorthand such as "Dr. J" to the existing `dr-jekyll`, and invented no duplicates; their new subjects were for things the vocabulary lacked. They sometimes left out a broad one such as `health`. That run loaded the whole vocabulary, about 8,000 tokens per write, which resolving now narrows. It was a single run over generated data, so it shows the direction, not settled numbers.
