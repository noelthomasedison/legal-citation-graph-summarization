# Step 1 — ingest + hierarchy report

- Passages loaded: 13,732 across 40 documents
- Fragment passages (path from doc order): 941
- Duplicate (doc, path) keys: 19 (48 passages involved)

## Hierarchy
- PARENT_OF edges: 12,629
- Non-root passages with a resolvable parent: 12,629/12,643 (99.9%)
- Depth distribution: {1: 1089, 2: 1698, 3: 4872, 4: 3700, 5: 1921, 6: 439, 7: 11, 8: 2}

## Gold CSV join via canonical paths
- Source (doc, canonical path) join: 1,611/1,628 (99.0%)  [raw-string join was 99.7%]
- Target (doc, canonical path) join: 1,512/1,560 (96.9%)  [raw-string join was 95.6%]
- Remaining target misses: 48
    - doc 7: `3.3.32` (canon: ('3', '3', '32'))
    - doc 3: `19.10.1` (canon: ('19', '10', '1'))
    - doc 3: `19.10.1` (canon: ('19', '10', '1'))
    - doc 3: `19.13.1` (canon: ('19', '13', '1'))
    - doc 3: `19.14.3` (canon: ('19', '14', '3'))
    - doc 3: `19.14.3` (canon: ('19', '14', '3'))
    - doc 3: `19.14.3` (canon: ('19', '14', '3'))
    - doc 3: `19.15.2` (canon: ('19', '15', '2'))
    - doc 3: `19.15.2` (canon: ('19', '15', '2'))
    - doc 3: `19.15.2` (canon: ('19', '15', '2'))

- Wrote /Users/noelthomasedison/Desktop/MSC Research/Research code base/phase1/data/processed/passages.jsonl
