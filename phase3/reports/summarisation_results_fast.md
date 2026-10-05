# Phase 3 — summarisation results (base / variant A / variant B / oracle)

EUR-Lex-Sum `test` split, **80 acts**, equal context
budget across all four conditions, single-pass generation (see
SUMMARISER_PLAN.md §2b for deviations). llama-3.3-70b, temperature 0.

## Means

| metric | base | variant A | variant B | oracle |
|---|---|---|---|---|
| rouge1_f | 0.4179 | 0.4146 | 0.4191 | 0.4150 |
| rouge2_f | 0.1588 | 0.1639 | 0.1629 | 0.1675 |
| rougeL_f | 0.2022 | 0.2022 | 0.2040 | 0.2063 |
| rouge1_p | 0.6734 | 0.6878 | 0.6804 | 0.6959 |
| bertscore_f | 0.8370 | 0.8388 | 0.8385 | 0.8412 |
| targeted | 0.1945 | 0.2673 | 0.2510 | 0.3467 |

## Paired contrasts

`A-base` = value of within-document references · `B-A` = value of
cross-document references (the supervisor's central question) ·
`oracle-B` = remaining headroom.

| contrast | metric | n | mean d | 95% CI | Wilcoxon p | win/loss |
|---|---|---|---|---|---|---|
| A-base | targeted | 32 | +0.0728 | [-0.0012, +0.1602] | 0.115 | 5/1 |
| A-base | rougeL_f | 80 | -0.0000 | [-0.0041, +0.0039] | 0.834 | 38/41 |
| A-base | bertscore_f | 80 | +0.0018 | [+0.0004, +0.0033] | 0.0679 | 46/32 |
| B-A | targeted | 32 | -0.0163 | [-0.1100, +0.0775] | 0.581 | 1/3 |
| B-A | rougeL_f | 80 | +0.0018 | [-0.0013, +0.0051] | 0.688 | 36/42 |
| B-A | bertscore_f | 80 | -0.0004 | [-0.0014, +0.0007] | 0.509 | 37/42 |
| B-base | targeted | 32 | +0.0565 | [-0.0581, +0.1771] | 0.394 | 5/2 |
| B-base | rougeL_f | 80 | +0.0017 | [-0.0019, +0.0055] | 0.41 | 42/36 |
| B-base | bertscore_f | 80 | +0.0015 | [+0.0000, +0.0030] | 0.0817 | 42/36 |
| oracle-B | targeted | 32 | +0.0957 | [+0.0195, +0.1966] | 0.0269 | 6/0 |
| oracle-B | rougeL_f | 80 | +0.0024 | [-0.0022, +0.0067] | 0.134 | 46/32 |
| oracle-B | bertscore_f | 80 | +0.0028 | [+0.0014, +0.0041] | 0.000381 | 52/27 |
| oracle-base | targeted | 32 | +0.1522 | [+0.0062, +0.3078] | 0.0723 | 9/2 |
| oracle-base | rougeL_f | 80 | +0.0041 | [-0.0007, +0.0087] | 0.0369 | 48/31 |
| oracle-base | bertscore_f | 80 | +0.0042 | [+0.0026, +0.0060] | 1.05e-06 | 57/22 |

## How to read

**`targeted` is the hypothesis test.** It measures coverage of exactly
the gold-summary sentences the base budget misses and a variant could
supply — the only place a ~2%-of-content effect can show. Aggregate
ROUGE/BERTScore are expected to be NULL (pre-registered as H3); a null
there is a property of the effect size, not a failure of the method.

**`rouge1_p` (precision) is the contamination check.** If variant B
imports material about a cited act that does not belong in a summary of
the focal act, precision falls even if recall does not.

**RePASs uses a pool identical across conditions** (base + every passage
any variant could add), so no condition is judged against more evidence
than another.
