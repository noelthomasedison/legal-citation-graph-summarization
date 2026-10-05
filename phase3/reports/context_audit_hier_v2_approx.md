# PRELIMINARY ONLY — approximate structural audit

Word-based whitespace counting was used because the official Llama
tokenizer was unavailable. This report is **not valid for final
token-budget verification or LLM generation**.

# Phase 3 v2 — context audit (DRY RUN, zero LLM calls)

Split `test`, 80 acts, seed 41. Tokenizer: `approximate_whitespace`. 
4 groups x 1800 tokens = a maximum complete Stage-1 prompt budget per group. Short Base groups
set a smaller effective budget shared by every condition.

## Treatment delivery (candidate availability is NOT delivery)

| quantity | count |
|---|---|
| sampled acts | 80 |
| A context differs from base | **61** |
| B context differs from A | **42** |
| B actually contains cross-document evidence | **42** |
| A comparisons with genuine treatment and balanced prompts | **59** |
| B comparisons with genuine treatment and balanced prompts | **39** |
| inserted cross evidence aligns with a gold sentence A missed | 3 |
| acts with >=1 a_actual_rescue sentence | 9 |
| acts with >=1 b_incremental_actual_rescue sentence | **3** |

## Target sentences for the pre-registered hypotheses

- H1 (B vs A, incremental rescue): **3** sentences across 3 acts
- H2 (A vs base, actual rescue): **16** sentences across 9 acts

## Complete Stage-1 prompt budgets

| condition | mean total | median total | max total |
|---|---|---|---|
| base | 6074 | 6507 | 7200 |
| A | 6072 | 6507 | 7200 |
| B | 6070 | 6486 | 7200 |
| oracle | 6072 | 6507 | 7200 |

Paired prompt differences across all acts (eligibility tolerance 1.0% per group):

- A-base: mean 0.03%, max 0.38%; largest group difference 23 tokens
- B-base: mean 0.07%, max 0.99%; largest group difference 44 tokens
- B-A: mean 0.04%, max 0.99%; largest group difference 44 tokens
- oracle-base: mean 0.04%, max 0.37%; largest group difference 19 tokens

- acts with at least one underfilled Base group: 72/80
- underfilled Base groups create a smaller effective budget; they do
  **not** permit A, B or Oracle to receive a longer prompt
- acts exceeding a per-group prompt cap: **0**
- acts where any treatment group is longer than its comparator: **0**
- duplicates REFUSED by the packer (correct): 1140 | ancestor/descendant overlaps refused: 28407
- duplicates that SURVIVED into a context (must be 0): **0**
- structural overlaps that SURVIVED (must be 0): **0**

## Context-hash equality (identical hash = identical evidence)

- A==base: 19/80
- B==A: 38/80
- oracle==base: 14/80

## Treatment by CELEX sector (B with cross evidence)

  sector 3: 42

## Power gate

- documents with balanced genuine B treatment: **39** (minimum 30)
- gate: **PASS**

n=30 is a minimum sanity threshold, **not** a guarantee of statistical
power. It only prevents generating on a sample that cannot possibly
show an effect.

## Provenance

- graph: `data/eurlex_edges_v2.jsonl` sha256 `3ab76ecc8bc424ad…`
- contexts: `data/contexts_hier_v2_test_approx.json` sha256 `0c5f1297f18aac51…`
- tokenizer mode: `approximate_whitespace`
- valid for generation: **false**

**Zero LLM calls were made by this script.**
