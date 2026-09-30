# One writer stream per machine

Each machine install appends only to its own stream of files, in its own folder under `events/`. Sessions on one machine take turns through an OS file lock; no two machines ever append to the same file.

## Alternative

All machines appending to one shared file.

## Why

The Brain's folders are kept in step by a sync service such as Google Drive or Dropbox. Two machines appending to one file would leave the sync service holding conflicting copies. With one stream per machine, only its own machine ever changes a stream, so each machine uploads its own stream and downloads the others', which it never writes.
