# AI.Brain

**Remember everything you choose to.** Tell Claude what happened. Hand it the documents. Ask it anything later.

AI.Brain gives Claude a journal to keep. Claude records whatever you tell it, files the documents that go with it, and answers questions about it months or years later, from what was recorded rather than from what anyone remembers.

## What it does

- **Captures what happens.** Tell Claude in your own words, in as much detail as you have. It asks follow-up questions to fill in what is missing, then records it, and offers to record something worth keeping that you mention in passing.
- **Files your documents.** Hand over a document or a folder of them. Each is moved into a folder structure organized for you to browse yourself, and recorded with what it says.
- **Answers from the record.** What happened, what was decided, how things stand now, what changed, and when. Answers are short, and the detail is there when you ask for it.
- **Keeps corrections honest.** Nothing is ever edited away. A correction is recorded beside the original, and every later answer reflects it.
- **Stays yours.** Everything lives in a folder you choose, as plain files. Put it in a synced folder, and every machine you point at it shares that Brain. Each Brain is its own folder and its own record: put everything in one, or keep separate Brains for what you want kept apart.

## At home

Record:

- *"Journal this: Dr. Jekyll moved me to four drops of Zorblax a day, starting tomorrow."*
- *"I had coffee with Bob at the Rusty Anchor today. He recommended a contractor named Hal for the kitchen."*

File:

- *"File this,"* with the contractor's quote attached.
- *"File everything in my scans folder."*

Ask:

- *"When is the hatchback due for its next service, and what did the last one find?"*
- *"Where did I meet Bob last month, and what did we talk about?"*
- *"Who was that contractor Bob recommended?"*
- *"How much have we spent on the kitchen remodel so far, and on what?"*
- *"Which cities did we visit on our trip to Narnia?"*

## At work

Record:

- *"Journal this: in the design review we picked the Zephyr design for billing. Sherlock owns the migration plan, due April 15. Still open: who signs off on the cutover."*
- *"Correct that: the migration plan is due the 22nd."*

File:

- *"File this,"* with the signed vendor contract attached.
- *"File the specs in this folder."*

Ask:

- *"What did we decide in Tuesday's design review, and why?"*
- *"What action items do I still owe from this week's meetings?"*
- *"Who asked about the export API, and what did I tell them?"*
- *"What's still open on the billing migration?"*

When Claude files a document somewhere new, it suggests where it should go and lets you choose. Once something like it has been filed, the next one goes beside it without asking.

## Install

AI.Brain is a plugin for Claude Code.

```bash
claude plugin marketplace add Velrea/AI.Brain
```

```bash
claude plugin install brain@ai-brain
```

When the plugin is enabled, Claude Code asks for your Brain folder. Choose a folder inside a synced folder, such as Google Drive or Dropbox, and choose the same one on every machine. Your records go in `events/` inside it, and your filed documents in `documents/`.

The plugin needs Python 3.11 or later on the machine: `python3` or `python` on macOS and Linux, `python` or `py` on Windows. The first session after installing or updating it downloads what the plugin needs, which takes about 20 seconds and needs a connection.

AI.Brain is in development.

## Learn more

- [The skills](docs/skills.md): the judgment Claude brings to recording, answering, and filing.
- [The core module](docs/core-module.md): how the record is kept, written, and read back.
- [The MCP server](docs/mcp-server.md): how Claude reaches the Brain, and how the plugin prepares the machine to run it.
- [Custom workflows](docs/workflows.md): using the Brain from a workflow of your own.
- [Development](docs/development.md): running the tests and the plugin from a working copy.
- [Work](docs/work/): what is being built, and the choices already settled for it.
- [Ideas](docs/ideas/): what might be worth doing, with no commitment.

## License

[Elastic License 2.0](LICENSE): you may use, copy, modify, and share it, but not offer it to others as a hosted or managed service.
