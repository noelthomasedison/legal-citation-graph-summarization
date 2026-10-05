# Step 2 — gold oracle + frozen split

## Gold edges
- Rows after exact-duplicate removal: 1,614
    - evaluable: 1,510
    - outsource (detection-only): 68
    - target not in structured JSON: 36
- Evaluable edges: 1,510 (Internal 945, External 565)

## Nested expansion (target 6.1 => all of 6.1.x)
- Targets that expand beyond themselves: 845/1,510 (56%)
- Expansion fan-out: median=2, mean=12.4, max=480
- Total (source, expanded-target) pairs: 18,656 (vs 1,510 flat)

## Frozen dev/test split (document level, by source doc)
- Dev docs (8): 2(301p), 4(169p), 7(767p), 10(507p), 11(1094p), 13(2220p), 22(128p), 31(101p)
- Dev edges: 840 | Test edges: 670

- Wrote /Users/noelthomasedison/Desktop/MSC Research/Research code base/phase1/data/processed/gold.jsonl and /Users/noelthomasedison/Desktop/MSC Research/Research code base/phase1/data/processed/splits.json
