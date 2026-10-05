# Phase 3 v2 — context audit (DRY RUN, zero LLM calls)

Split `test`, 80 acts, seed 41. Tokenizer: `meta-llama/Llama-3.3-70B-Instruct`.
4 groups x 1800 tokens = a maximum complete Stage-1 prompt budget per group. Short Base groups
set a smaller effective budget shared by every condition.

## Treatment delivery (candidate availability is NOT delivery)

| quantity | count |
|---|---|
| sampled acts | 80 |
| A context differs from base | **73** |
| B context differs from A | **36** |
| B actually contains cross-document evidence | **36** |
| A comparisons with genuine treatment and balanced prompts | **59** |
| B comparisons with genuine treatment and balanced prompts | **33** |
| inserted cross evidence aligns with a gold sentence A missed | 2 |
| acts with >=1 a_actual_rescue sentence | 7 |
| acts with >=1 b_incremental_actual_rescue sentence | **2** |

## Target sentences for the pre-registered hypotheses

- H1 (B vs A, incremental rescue): **2** sentences across 2 acts
- H2 (A vs base, actual rescue): **8** sentences across 7 acts

## Complete Stage-1 prompt budgets

| condition | mean total | median total | max total |
|---|---|---|---|
| base | 6684 | 7180 | 7200 |
| A | 6676 | 7172 | 7200 |
| B | 6674 | 7172 | 7200 |
| oracle | 6681 | 7168 | 7200 |

Paired prompt differences across all acts (eligibility tolerance 1.0% per group):

- A-base: mean 0.13%, max 1.14%; largest group difference 49 tokens
- B-base: mean 0.16%, max 1.17%; largest group difference 53 tokens
- B-A: mean 0.04%, max 0.88%; largest group difference 53 tokens
- oracle-base: mean 0.05%, max 0.47%; largest group difference 34 tokens

- acts with at least one underfilled Base group: 68/80
- underfilled Base groups create a smaller effective budget; they do
  **not** permit A, B or Oracle to receive a longer prompt
- acts exceeding a per-group prompt cap: **0**
- acts where any treatment group is longer than its comparator: **0**
- duplicates REFUSED by the packer (correct): 739 | ancestor/descendant overlaps refused: 22918
- duplicates that SURVIVED into a context (must be 0): **0**
- structural overlaps that SURVIVED (must be 0): **0**

## Context-hash equality (identical hash = identical evidence)

- A==base: 7/80
- B==A: 44/80
- oracle==base: 8/80

## Treatment by CELEX sector (B with cross evidence)

  sector 3: 36

## Citation evidence representation

- mode: **citation cards**
- frozen source-target requests: **789**
- verifier-approved usable cards loaded: **358**
- missing card records: **0**

## Power gate

- documents with balanced genuine B treatment: **33** (minimum 30)
- gate: **PASS**

n=30 is a minimum sanity threshold, **not** a guarantee of statistical
power. The explicit override permits an engineering pilot only; the
full experiment must still pass this gate.

## Provenance

- graph: `data/eurlex_edges_v2_3.jsonl` sha256 `dd20dbfe073eb544…`
- contexts: `data/contexts_hier_v2_test_citation_card_full_v4.json` sha256 `a781a73c431a5e51…`
- tokenizer mode: `exact`
- valid for generation: **true**

**Zero LLM calls were made by this script.**
