# Phase 3 prerequisites — EU graph construction and variant-A viability

Frozen Phase-1 detector/resolver, zero retuning; aliases + FSMR off (EU
acts cite by CELEX, not informal alias). Scope: **1504 acts**.

## P1 — segmentation

- passages: **260,149**
- per act: median 72, mean 173, max 8267
- depth distribution (1=Article, 2=paragraph, 3=point): {1: 53774, 2: 119277, 3: 87098}

## P2 — resolution (the number we never had)

- mentions detected: **455,810**
- resolved to a passage: **260,535**
- unresolved: 195,275 | ambiguous drops: 9,640
- **resolution rate: 57.2%**  (ADGM ~ tuned corpus; CUAD 38.9%)
- unique within-document edges: **175,976**

**Guard activity** (mentions REFUSED rather than force-resolved — the fix for the ~37% false-positive rate found in `eurlex_audit_sample.md`):
- refused: names a third-country instrument (Law/Decree/Treaty/…): **8,267**
- refused: target inside an unmodelled Annex/Appendix/Schedule: **5,533**
- routed to another EU act we hold, via CELEX: **7,856**
- cross-document citations resolvable via CELEX (target in corpus): **17,915**

## P3 — density and community viability (decides variant A)

- edges per passage: **0.68**  (ADGM ~0.50)
- Louvain communities (per act, seed 41): 125,373
- community size: median 1, mean 1.8, max 420
- communities of size >= 2: **9,808**
- **passages inside a non-trivial community: 40.2%**

**Verdict rule (pre-registered in SUMMARISER_PLAN.md §3.1):** if most
passages fall into singleton communities, community chunking
degenerates into linear chunking and variant A collapses toward base.
Measured: 40.2% of passages sit in a community
of size >= 2.

## What this decides

- **P2 gates everything**: no resolved edges, no graph, no variants.
- **P3 gates variant A only.** Variant B (cross-document augmentation)
  depends on CELEX matching, which is independent of within-document
  density — so B remains testable even if A is not viable.
