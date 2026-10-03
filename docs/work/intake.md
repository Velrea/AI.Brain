# Intake

Promoted from the idea Intake.

An `intake` skill files a document into the Brain: handed a file, it decides where the file belongs among the Brain's documents, moves it there, and writes the one journal entry that carries its contents. The point of filing is to pull a document up again later, through the journal or by hand.

## Decided

- **The document moves; it is not copied.** Intake takes the file from where it is and puts it in the Brain, so one copy remains and it is the filed one.
- **The documents folder is organized for a person to browse.** The user goes to the folder directly and finds what they want by its folder structure, so the structure must make sense to them. Intake builds that structure up as documents arrive, rather than following a scheme fixed in advance.
- **The entry carries the document's contents**, as the journal skill's guidance holds, and names the filed document by path and `sha256`.
- **A website is never copied into the Brain.** Intake files documents; a web page stays where it is.

## Suggested

- `store_document` copies and leaves the source where it is, so moving may mean the tool gains a way to move, rather than the skill removing the source itself.
- Intake looks at the folders already there before choosing a path, so similar documents land together.
- A folder of documents handed over at once is filed one document at a time, each with its own entry.

## Depends on

- The journal and query skills

## Done when

- Handed a file, `intake` moves it into a folder of the Brain's documents that a person browsing would look in, and writes one journal entry carrying its contents and naming it by path and `sha256`.
