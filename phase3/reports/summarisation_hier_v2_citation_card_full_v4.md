# Phase 3 v2 — hierarchical summarisation results

Split `test`, 80 acts with summaries. One-level hierarchy
(evidence -> group briefs -> summary), identical per-group token budget
for every condition. Pre-registered in PHASE3_V2_HIERARCHICAL_PLAN.md.

## PRIMARY H1 — variant B vs variant A

Measured only on `b_incremental_actual_rescue_idx`: gold sentences that
A's actual evidence did NOT cover and B's actual evidence did. This
isolates what cross-document evidence adds over within-document evidence.

| contrast | n | mean d | 95% CI | Wilcoxon p | w/t/l | verdict |
|---|---|---|---|---|---|---|
| B-A (H1) | — | — | — | — | — | insufficient data |

### H1 across three populations (reported together)

| population | n | mean d | p | verdict |
|---|---|---|---|---|
| all acts with Base-missed sentences | 60 | +0.0139 | 0.18 | no statistically detectable difference was observed |
| balanced genuine-B treatment | 27 | +0.0309 | 0.18 | no statistically detectable difference was observed |
| incremental actual-rescue subset | — | — | — | insufficient data |

## SECONDARY H2 — variant A vs base

| contrast | n | mean d | 95% CI | Wilcoxon p | w/t/l | verdict |
|---|---|---|---|---|---|---|
| A-base (H2) | 7 | +0.2143 | [+0.0000, +0.5000] | 0.5 | 2/5/0 | no statistically detectable difference was observed |

## Where targeted content is lost in the hierarchy

Coverage of the targeted gold sentences at each stage. A drop between
columns localises the failure:

- evidence -> brief: **compression failure** (Stage 1 discarded it)
- brief -> final: **composition failure** (Stage 2 discarded it)
- low at evidence: **retrieval failure** (it never entered the context)

| condition | target | n | evidence | brief | final |
|---|---|---|---|---|---|
| base | h1 | 2 | 0.000 | 0.000 | 0.000 |
| base | h2 | 7 | 0.000 | 0.214 | 0.357 |
| A | h1 | 2 | 0.500 | 0.500 | 0.000 |
| A | h2 | 7 | 0.786 | 0.286 | 0.571 |
| B | h1 | 2 | 0.500 | 0.500 | 0.500 |
| B | h2 | 7 | 0.786 | 0.286 | 0.571 |
| oracle | h1 | 2 | 1.000 | 0.500 | 1.000 |
| oracle | h2 | 7 | 0.786 | 0.143 | 0.286 |

## Aggregate metrics (descriptive only)

| metric | base | A | B | oracle |
|---|---|---|---|---|
| ROUGE-1 | 0.4283 | 0.4368 | 0.4400 | 0.4481 |
| ROUGE-2 | 0.1545 | 0.1612 | 0.1605 | 0.1745 |
| ROUGE-L | 0.1935 | 0.1963 | 0.1970 | 0.2064 |
| ROUGE-1 precision | 0.6539 | 0.6558 | 0.6515 | 0.6809 |

| metric | base | A | B | oracle |
|---|---|---|---|---|
| BERTScore-F1 | 0.8342 | 0.8347 | 0.8342 | 0.8379 |

## Oracle arm — diagnostic only

Oracle evidence is selected **using the reference summary**. It is
target-leaking and not deployable. It bounds what better evidence
selection could achieve; it does **not** demonstrate that the citation
graph works, and it is not used to support any claim about A or B.

## Reporting language

Contrasts with p >= 0.05 are reported as *no statistically detectable
difference was observed*. No hypothesis in this report is described as
proved, and no non-significant result is described as a confirmed null.

RePASs is not run in v2: the v1 scoring run was stopped, and the
metric has not been validated for abstractive EUR-Lex summarisation.
