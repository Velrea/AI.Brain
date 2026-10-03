# AI.Brain

**Your life, on the record.** Tell Claude what happened. Hand it the paperwork. Ask it anything later.

You already tell Claude about your day: the mechanic's verdict, the new prescription, the call with the landlord. Then the conversation ends, and it is gone. AI.Brain gives Claude somewhere to keep it. Claude writes down what happens in your life, files the documents that go with it, and answers questions about it months or years later, from what was actually recorded rather than from what anyone remembers.

## A year with a Brain

**March.** Back from the shop, you tell Claude: *"Oil change on the blue hatchback. They said the rear brakes are getting thin."* Claude asks the mileage and the shop's name, then records it.

**March, a minute later.** *"File this,"* with the invoice attached. Claude reads it, files it at `assets/blue-hatchback/service/2026-03-14-oil-change-invoice.pdf` beside the car's other service records, and writes down what the invoice says, so its line items can be found without opening it.

**June.** *"Dr. Jekyll doubled my Zorblax to four drops."* Recorded, under both the doctor and the medication.

**July.** *"Actually, it was three drops, not four."* The mistake is corrected, and the original account is kept, so you can always see what was said and what was fixed.

**August.** Planning your week with Claude, you mention the landlord agreed to fix the fence by Friday. Claude asks whether to record it, and does when you say yes.

**September.** *"When were the brakes last looked at, and what did they say?"* Claude finds the March visit and the invoice, and answers in two sentences, offering the rest if you want it.

**November.** *"What medications am I on now?"* Claude reads everything recorded about your medications, works out where each one stands today, and offers to save the answer, so asking again next month is instant.

## What it does

- **Captures what happens.** Tell Claude in your own words, in as much detail as you have. It asks follow-up questions to fill in what is missing, then records it, and offers to record something worth keeping that you mention in passing.
- **Files your documents.** Hand over an invoice, a lab report, or a folder of scans. Each is moved into a folder structure organized for you to browse yourself, and recorded with what it says.
- **Answers from the record.** What happened, how things stand now, what changed, and when. Answers are short, and the detail is there when you ask for it.
- **Keeps corrections honest.** Nothing is ever edited away. A correction is recorded beside the original, and every later answer reflects it.
- **Stays yours.** Everything lives in a folder you choose, as plain files. Put it in Google Drive or Dropbox, and every machine you use shares one Brain.

## How you use it

You talk to Claude the way you would anyway. Some things to try:

- *"Journal this: the vet says the dragon's scales are clearing up."*
- *"File this document."* or *"File everything in my Downloads/scans folder."*
- *"What did the vet say about the dragon's scales last spring?"*
- *"How has my Zorblax dose changed this year?"*
- *"That's wrong, the appointment was on the 12th."*

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
