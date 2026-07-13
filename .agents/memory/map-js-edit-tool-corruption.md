---
name: Edit tool corrupted map.js on multi-line replacements
description: The Edit tool duplicated the entire file 3-5x and truncated a string literal when replacing a multi-line block in this project's map.js. Use Python/sed for risky multi-line JS edits here instead.
---

While restyling `airdna-project/08-rentalizer/static/map.js`, two separate
`Edit` calls that replaced a multi-line block (a `const LAYER_DEFS = {...}`
block plus a new helper function above it) caused the file to balloon from
~940 lines to 4000-12000+ lines (the same block duplicated repeatedly), and
also truncated a string literal (`return '$' + ...` got cut to `return '`)
in a way that broke `node -c` syntax checking. This happened twice in a row
with the same edit, so it's reproducible for this kind of edit, not random.

**Why it matters:** the corruption was silent in the browser — Leaflet still
rendered because JS `function` redeclarations don't throw (last one wins),
so the map page looked fine even though the served file was a garbled mess
of dead duplicate code. Only `node -c static/map.js` or `wc -l` surfaced it.

**How to apply:** for any large/multi-line replacement in this file (or if
you see a file's line count jump far more than the diff should produce),
verify with `wc -l` and `node -c <file>` (or the language's syntax checker)
immediately after the edit. If corrupted, `git checkout -- <file>` to reset
to the last clean commit, then redo the edit via a Python script that reads
the file, asserts `content.count(old) == 1`, does `.replace()`, and writes
back — this reliably avoided the bug where the Edit tool did not.
