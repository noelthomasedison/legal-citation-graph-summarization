# Phase 1 Progress Summary — Supervisor Update (July 2026)

One consolidated view; every number traces to a detailed report in `phase1/reports/`.

## What exists

A complete, rerunnable pipeline (`phase1/`) that automatically extracts the
structural knowledge graph RegGraph built by hand, and evaluates every stage
against the manually-curated gold cross-reference table.

Pipeline: **Segment → Detect → Resolve → Assemble**, with the evaluation
harness built *before* the extractor. Rules tuned on 8 dev documents only;
the 32 test documents remain untouched (one-shot final run pending).

## The substrate (audit.md, step1_ingest.md)

| Fact | Value |
|---|---|
| Documents / passages | 40 / 13,732 |
| Distinct PassageID formats | 202 (941 fragment-only IDs resolved via doc order) |
| Hierarchy (PARENT_OF) | 12,629 edges; 99.9% of non-root passages resolve a parent |
| Gold rows | 1,628 (−14 exact duplicates → 1,614) |
| Evaluable gold edges | 1,510 (945 Internal, 565 External) |
| Outsource rows (detection-only) | 68 |
| Excluded: target absent from JSON | 36 (2.3%; docs 3 & 7 — version mismatch, documented) |
| Join integrity (UID-first + canonical path) | 100% source / 97.7% target |
| Nested expansion | 56% of targets expand; mean fan-out 12.4; 18,656 expanded pairs |

Data-quality findings passed back to the group: version-mismatched gold rows,
duplicate-path passage records ("10.3.2.(4)" and "10.3.2.4" both exist),
Unicode control chars in text, parent passages duplicating child text.

## Extractor scores — DEV set (step3_rules_dev.md)

Recall vs gold (840 dev edges), three pre-registered credit modes:

| Credit mode | All | Internal | External |
|---|---|---|---|
| Exact target | 0.881 | 0.953 | 0.553 |
| Nested (6.1 ⇒ 6.1.x) | 0.886 | 0.959 | 0.553 |
| Nested + source-nested | **0.896** | **0.969** | 0.566 |

Detection is near-solved (2 missed mentions among 121 analysed errors);
the residual is resolution of external references without an explicit
rulebook name.

## Precision — the key finding (audit_results.md)

- Measured against the gold CSV: **0.24** — invalid as a metric, because
  inspection proved the gold **non-exhaustive** (verifiably real references,
  e.g. "Without limiting Rule 1.7.1…", have no gold row).
- Manual stratified audit (n=100, seed=13, by resolution provenance):
  **weighted true precision 0.885**. Safest stratum (53% of predictions): 15/15.
- Error taxonomy from the audit (E1 table artefacts; E2 cross-doc mis-routing)
  → both fixed; verified against audit labels: 21+/25 sampled false edges
  removed, 0 true edges lost, recall unchanged.
- Protocol (PLAN.md amendments 1 & 2, documented before the test run):
  recall vs gold = primary automatic metric; precision via fresh manual audit
  on the frozen config at test time; audited-true edges absent from gold =
  **candidate extension of the group's gold resource** (proposed deliverable).

## Decisions requested

1. Pre-register test-set success thresholds (e.g. Internal R ≥ 0.90) before the one-shot run.
2. Approve evaluation amendments 1 & 2 (PLAN.md).
3. Adjudicate 3 UNSURE audit items (audit_results.md).
4. Gold-extension deliverable — useful to the group?
5. LLM arm provider: free open-weight endpoints (Groq / NVIDIA Build); ADGM data is public.

## Next

Ablation ladder → LLM extractor arm (rules-vs-LLM targets the external
residual) → one-shot test run + fresh precision audit → Phase 1 report →
Phase 2 (reference-aware retrieval on ObliQA).
