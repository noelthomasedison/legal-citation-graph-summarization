# Phase 1 — Structural KG Extraction + Gold Evaluation (ObliQA/ADGM)


## Goal
Automate the graph RegGraph built by hand — segment → detect → resolve → assemble — and
evaluate every stage against the manually-curated gold cross-reference table
(`CrossReferenceData.csv`, curated by Tuba). Training-free methods only.

## Design principles
1. Harness-first: the evaluator is built before any extractor.
2. Deterministic-first: regex+schema rules before the LLM arm; every stage ablatable.
3. Document-level dev/test split; test docs never inspected during rule development.
4. Pre-registered correctness semantics (below) — no post-hoc metric changes.

## Layout
- `data/raw/GraphRAG4RegGraph/` — clone of the RegNLP repo (read-only substrate)
- `data/processed/` — normalised passages, gold edges (flat + expanded), frozen splits
- `src/regkg/` — ingest, ids (normalisation), hierarchy, gold, detect, resolve,
  llm_extract, graph, evaluate, splits
- `scripts/` — numbered pipeline steps 00–05
- `reports/` — audit + evaluation outputs

## Build steps
0. **Audit** — edge counts, ID formats, CSV↔JSON join integrity. Drives all decisions.
1. **Ingest + ID normalisation** — `ids.py` canonicalises passage IDs
   (`19.2.17`, `PART 5.12.3.6.(3)`, `Part 11.Chapter 4.114.(2)`) into comparable tuples.
   Most-unit-tested module.
2. **Gold oracle** — flat gold (CSV rows) + expanded gold (nested: target 6.1 ⇒ all
   descendants, per RegGraph README warning). Freeze dev (~8 docs, size-stratified,
   incl. PRU) / test split.
3. **Rule extractor** — detect (Rule/Section/Part patterns, "as defined in",
   doc abbreviations FSMR/GLO/…) + resolve (within-doc lookup → cross-doc alias map →
   nested expansion). Dev docs only for tuning.
4. **LLM extractor arm** — typed JSON schema, few-shot, cached; dev subset first.
5. **Evaluate + report** — P/R/F1 vs flat & expanded gold; breakdowns
   Internal/External, exact-vs-nested, doc-size buckets; ablation ladder; error
   taxonomy of ~50 sampled misses.

## Correctness semantics (pre-registered, amended — see log)
Extracted edge (src, tgt) is correct iff src matches a gold row source AND tgt equals
the gold target (exact) or lies in its nested expansion (nested-credit). Both reported.
Detection and resolution also scored separately (detection ≈ gold ReferenceText found
in source passage) to distinguish "missed mention" from "wrong resolution".

AMENDMENT 1 (2026-07-02, documented before test run): a THIRD credit mode
"source-nested" is reported alongside: the prediction source may be an
ancestor/descendant of the gold source. Rationale: the corpus duplicates child
text inside parent passages and the gold mixes source-attachment conventions,
so strict source matching penalises attribution, not extraction.

AMENDMENT 2 (2026-07-02): precision against the gold CSV is NOT a valid
quality metric — step-3 inspection proved the gold is non-exhaustive (real
references verifiably missing from it). Primary automatic metric = RECALL vs
gold (all three credit modes); precision estimated by MANUAL AUDIT of a
random sample of predictions (~100), IR-pooling style. Predicted edges that
survive the audit but are absent from gold form a candidate gold EXTENSION —
a deliverable in its own right.

## Pre-registered test thresholds (fixed 2026-07-14, BEFORE the one-shot test run)

Registered by the candidate from dev-set evidence after the supervisor delegated
threshold-setting; emailed to the supervisor before execution. Rationale: dev
scores (nested + source-nested credit) are All 0.896 / Internal 0.969 /
External 0.566; the rules were tuned on dev, so a ~0.05 generalisation drop is
allowed before the method is judged to have overfit.

SUCCESS iff, on the sealed 32 test documents, frozen config, single run:
  T1  Internal recall >= 0.90
  T2  Overall recall  >= 0.80
  T3  External recall >= 0.45
  T4  Audited precision >= 0.80 (fresh stratified audit, n=100, seed fixed
      in advance = 41, same stratification protocol as dev)

Failure handling (also pre-registered): if any threshold is missed, the result
is reported as-is with an error analysis; NO re-tuning on test data under any
circumstances. A miss on T3 alone is reported as "cross-document resolution
does not generalise", not as overall failure.

## Risks
- Passage-ID normalisation is the hidden hard problem → over-test `ids.py`.
- Gold CSV may itself be incomplete (manual curation) → report precision "errors"
  qualitatively; some may be gold misses, not extractor errors.
- If the extractor can't approach gold quality, contribution pivots to the evaluation
  methodology + nested-resolution analysis (known fallback, decide end of Wk 2).
