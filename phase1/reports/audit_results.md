# Precision audit results (dev, seed=13, adjudicated 2026-07-02)

- S1_safe: n=15 TRUE=15 FALSE=0 UNSURE=0 -> precision 1.00 (weight 0.53)
- S2_bare: n=25 TRUE=10 FALSE=13 UNSURE=2 -> precision 0.40 (weight 0.08)
- S3_crossdoc: n=30 TRUE=19 FALSE=11 UNSURE=0 -> precision 0.63 (weight 0.14)
- S4_nonexact: n=30 TRUE=28 FALSE=1 UNSURE=1 -> precision 0.93 (weight 0.25)

**Weighted true precision (conservative): 0.885**
(vs 0.24 measured against the non-exhaustive gold CSV)

## Error taxonomy
- E1 table/item-label artefacts + numeric-table decimals -> S2 failures
- E2 Chapter/PART heading echoes, same-doc chapters mis-routed to FSMR,
  unknown external docs (PRMS, unaliased guidance) force-resolved -> S3 failures
- UNSURE (3): fee-table rule numbers with garbled columns (2), A2.1.3 ascent (1)
