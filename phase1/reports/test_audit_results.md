# TEST precision audit results (seed=41, adjudicated 2026-07-14)

- S1_safe: n=15 TRUE=15 FALSE=0 -> precision 1.000 (weight 0.415)
- S2_bare: n=25 TRUE=23 FALSE=2 -> precision 0.920 (weight 0.013)
- S3_crossdoc: n=30 TRUE=29 FALSE=1 -> precision 0.967 (weight 0.247)
- S4_nonexact: n=30 TRUE=29 FALSE=1 -> precision 0.967 (weight 0.326)

**Weighted true precision: 0.980**  ->  T4 (>= 0.80): PASS

## The 4 FALSE edges (error classes)
- 023: suffix mis-resolution within doc (18.1.3 -> 13.3.18) — rare suffix collision
- 025: guidance item-label self-echo (A2.15.Guidance.7 inline in parent text)
- 060: cross-doc suffix collision (COBS 8.2(c) -> 6.8.2(c); 8.2(c) absent as passage)
- 089: list continuation loses alias routing (GEN 3.3.19, 7.2.7 -> 7.2.7 resolved in source doc)

No UNSURE items. Dev audit (pre-fix config) was 0.885; the audit-driven
fixes generalised — test precision is substantially higher.
