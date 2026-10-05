# Step 6 — ONE-SHOT TEST RUN (sealed docs, frozen config)

- Test documents: 32 | passages: 8,445
- Test gold edges (evaluable): 670 (Internal 257, External 413)
- Predicted edges: 4,030 | unresolved mentions: 1,273 | ambiguous drops: 826

| Credit mode | All | Internal | External |
|---|---|---|---|
| Exact | 0.806 | 0.938 | 0.724 |
| Nested | 0.816 | 0.946 | 0.736 |
| Nested + source-nested | 0.825 | 0.957 | 0.743 |

## Threshold verdicts (nested + source-nested, as pre-registered)
- T1 Internal recall: 0.957 vs >= 0.90  ->  PASS
- T2 Overall recall: 0.825 vs >= 0.80  ->  PASS
- T3 External recall: 0.743 vs >= 0.45  ->  PASS
- T4 audited precision >= 0.80: PENDING adjudication of the seed-41 sample below

## Recall by document size (nested + source-nested)
- small (<200p): R=0.765 (gold n=255)
- medium (200-800p): R=0.840 (gold n=187)
- large (>=800p): R=0.882 (gold n=228)

- Audit sample written: 100 edges, population S1_safe=1672, S2_bare=51, S3_crossdoc=995, S4_nonexact=1312
