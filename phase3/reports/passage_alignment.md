# Phase 3 — passage-level alignment (oracle targets + rescueable sentences)

Split `test`, 80 acts, base budget **12 passages**, coverage threshold 0.6. Seeded random sample (seed 41). No LLM calls.

Selection conditions only on centroid ranks and graph structure, both
fixed before generation — never on model output.

| quantity | value |
|---|---|
| acts prepared | 80 |
| passages per act (mean) | 246 |
| summary sentences MISSED by the base budget | **9.7%** |
| of those, rescued by **variant A** (within-doc closure) | **15.1%** |
| of those, rescued by **variant B** (+ cross-doc closure) | **17.6%** |
| acts with >=1 cross-doc passage available (B CAN differ from A) | **42/80** |

## Reading

The last row is a PRECONDITION, not a result: variant B can only differ
from variant A on acts where cross-document material exists at all. On
2026-08-10 this was 16/80 and B was byte-identical to A for 47/80 acts
(the 4-slot cap was consumed by within-document additions listed first).
Generating under those conditions would have compared A with itself.

The MISSED row is the headroom: content the base condition cannot
produce. The A and B rows are how much of that headroom each variant
could in principle supply — the ceiling on any generation gain, computed
before a single token is generated. If B ~ A here, the cross-document
arm has little room to differ and H1 (B > A) is unlikely to show.

Written: `data/align_test.json` (contexts + per-sentence labels
for the targeted metric).
