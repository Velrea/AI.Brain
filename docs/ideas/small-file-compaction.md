# Small-file compaction

Concerns storage.

Merge the event store's small files into fewer, larger ones, so a long list of files never slows reading.

File count, more than entry count, sets how long a read takes: about 4,000 entries spread over 500 weekly files took about 130 ms to search, where 200,000 entries in 20 large files took about 45 ms. Rolling every 7 days alone gives each machine about 52 files a year.

Small files come from a machine that writes rarely, from a machine that dies or is lost while it holds an open file, and from a machine that loses its local state and starts a new file. Each machine appends only to files it created, and the store never says which machine owns which file, so a file left behind is never sealed by its owner.

- **Files carry a prefix.** `h-<uuidv7>.jsonl` is hot: only the machine that created it appends to it. `c-<uuidv7>.jsonl` is compacted: written once by the compactor and never appended to.
- **A writer rolls to a new `h-` file when its current one is 7 days old**, by the time in its own name, or when it reaches 10,000 lines. A writer whose file has vanished starts a new one and records it in its local state.
- **The compactor takes an `h-` file once it is older than 7 days plus a 30-day grace**, and a `c-` file at any time. The grace covers sync delay and clocks that disagree between machines: a laptop can append on day 6 while offline and sync on day 20.
- **No lock reaches across machines.** An OS lock holds only on the machine that takes it, and every machine appends to its own synced copy. A compactor that deleted a file another machine was still appending to would leave the sync service holding a delete against an edit, and the edit could be lost. The compactor therefore never touches a file that might still be written.
- **No machine is chosen to compact.** Choosing one across machines that share only a sync folder needs prompt delivery and agreeing clocks, which a sync folder does not give. Compaction is made safe to run twice instead: any machine may run it, at most once a day under its local lock, and a local setting can turn it off on a machine.
- **Compaction writes and never deletes in the same pass.** It merges what it may take into a new `c-` file ordered by `event_date`, dropping duplicate `id`s.
- **A file is deleted only when a newer `c-` file, at least a day old, holds every `id` in it.** Checking the ids needs no manifest. *Newer*, by the UUIDv7 name, breaks the tie when two compactors merge the same inputs: every machine deletes the older output and keeps the newer. *A day old* lets sync spread the new file before its sources go.
- **Readers skip duplicate `id`s**, which covers the time between a merge and the deletes, and two compactors running at once.
- **Compaction leaves snapshots alone.** A merged record keeps its `recorded_at`, which is all a snapshot's reach-back looks at.

The one loss left is a machine offline with unsynced writes for longer than the grace.

It sits beside Parquet compaction, which converts sealed files to Parquet; the two may meet.

Open: loose ends and testing remain. How a sync service settles a delete against an edit is untested. The 7 days and the 30-day grace are proposed defaults, not settled.
