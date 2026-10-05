# Step 4 — ablation ladder (dev set, nested + source-nested credit)

| Rung | Pred edges | R all | R int | R ext | Unresolved | Ambiguous |
|---|---|---|---|---|---|---|
| R1 core grammar | 2,567 | 0.761 | 0.929 | 0.000 | 1,237 | 0 |
| R2 + guards | 2,394 | 0.761 | 0.929 | 0.000 | 910 | 0 |
| R3 + alias table | 2,453 | 0.810 | 0.930 | 0.263 | 793 | 0 |
| R4 + FSMR fallback | 2,453 | 0.811 | 0.930 | 0.270 | 791 | 0 |
| R5 + suffix/ascent | 2,793 | 0.896 | 0.969 | 0.566 | 338 | 116 |
| R6 + attribution (full) | 2,768 | 0.896 | 0.969 | 0.566 | 337 | 115 |

## Leave-one-out (full system minus one component)

| Removed | Pred edges | R all | R int | R ext |
|---|---|---|---|---|
| − (nothing — full) | 2,768 | 0.896 | 0.969 | 0.566 |
| − guards | 2,950 | 0.896 | 0.969 | 0.566 |
| − alias table | 2,790 | 0.877 | 0.969 | 0.461 |
| − FSMR fallback | 2,730 | 0.880 | 0.969 | 0.474 |
| − suffix/ascent | 2,432 | 0.811 | 0.930 | 0.270 |
| − attribution | 2,793 | 0.896 | 0.969 | 0.566 |

## Graph-scope view at full config (variant A vs B)
- Variant A (internal-only KG): 2,518 edges -> recall vs internal gold: 0.969
- Variant B adds 250 cross-document edges -> recall vs external gold: 0.566
- B/A edge ratio: 0.10 extra edges per internal edge

Reading: rungs 1-2 are, in effect, the internal-only world; rungs 3-5 are
the cross-document machinery. The A/B split above is the same story at the
graph level — it is what Phases 2-3 will consume as variants A and B.
