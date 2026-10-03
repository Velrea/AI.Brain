# AI.Brain

**Remember everything you choose to.** Tell Claude what happened. Hand it the documents. Ask it anything later.

You already tell Claude what is going on: the decision from this morning's meeting, the vendor's new quote, what the mechanic said. Then the conversation ends, and it is gone. AI.Brain gives Claude a journal to keep it in. Claude writes down whatever you want to remember, at work or at home, files the documents that go with it, and answers questions about it months or years later, from what was actually recorded rather than from what anyone remembers.

## A year with a Brain

**March.** After a meeting you tell Claude: *"We picked the Zephyr design for the billing service. Sherlock owns the migration plan, due April 15. Still open: who signs off on the cutover."* Claude asks who else was there, then records the decision, the action item, and the open question.

**March, a minute later.** *"File this,"* with the signed vendor contract attached. Claude reads it, files it beside your other contracts with that vendor, and writes down what it says, so its renewal terms can be found without opening it.

**June.** Back from the shop: *"Oil change on the blue hatchback. They said the rear brakes are getting thin."* Recorded, under the car.

**July.** *"Actually, the migration plan is due the 22nd, not the 15th."* The mistake is corrected, and the original account is kept, so you can always see what was said and what was fixed.

**August.** Planning your week with Claude, you mention the landlord agreed to fix the fence by Friday. Claude asks whether to record it, and does when you say yes.

**September.** *"What did we agree with the vendor about renewal?"* Claude finds the contract's entry and the meeting where it came up, and answers in two sentences, offering the rest if you want it.

**November.** *"What's still open on the billing migration?"* Claude reads everything recorded about it, works out what is done and what is not, and offers to save the answer, so asking again next month is instant.

## What it does

- **Captures what happens.** Tell Claude in your own words, in as much detail as you have. It asks follow-up questions to fill in what is missing, then records it, and offers to record something worth keeping that you mention in passing.
- **Files your documents.** Hand over a contract, a spec, an invoice, or a folder of scans. Each is moved into a folder structure organized for you to browse yourself, and recorded with what it says.
- **Answers from the record.** What happened, what was decided, how things stand now, what changed, and when. Answers are short, and the detail is there when you ask for it.
- **Keeps corrections honest.** Nothing is ever edited away. A correction is recorded beside the original, and every later answer reflects it.
- **Stays yours.** Everything lives in a folder you choose, as plain files. Put it in a synced folder, and every machine you use shares one Brain.

## How you use it

You talk to Claude the way you would anyway. Some things to try:

- *"Journal this: the design review moved to Thursday, and we're dropping the export feature from this release."*
- *"File this document."* or *"File everything in my Downloads/scans folder."*
- *"What did we decide about the export feature, and why?"*
- *"What action items do I still owe from last week's meetings?"*
- *"That's wrong, the review was on the 12th."*

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
- [Development](docs/development.md): running the tests and the plugin from a working copy.
- [Work](docs/work/): what is being built, and the choices already settled for it.
- [Ideas](docs/ideas/): what might be worth doing, with no commitment.

## License

[Elastic License 2.0](LICENSE): you may use, copy, modify, and share it, but not offer it to others as a hosted or managed service.
