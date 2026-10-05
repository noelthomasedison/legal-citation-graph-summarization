# Phase 3 — Dataset Selection Plan (the gate study)

Status: **Stage 1 done (feasibility measured); Stage 2 not started.**
Revised August 2026 after (a) Tuba's dataset suggestions and (b) the
EUR-Lex-Sum probe (`phase3/scripts/01_eurlexsum_gate.py` →
`phase3/reports/eurlexsum_gate.md`). Phase 3 proper — the summarisation
method — does not start until the remaining gate is measured and the
supervisor agrees.

## 1. Objective

Choose the Phase 3 corpus by **measurement, not assumption**. Phase 2 proved
that a citation-based method only helps when the benchmark's evidence is
citation-linked *at the frontier the method actually uses* — ObliQA (0.5%
linked) was a guaranteed null; ObliQA-XRef (90%) a large win; CUAD (3.2%
rescueable) worked exactly where it fired. The same gate applies here, before
any expensive experiment.

**The requirement that kills most candidates:** one corpus that is BOTH
(a) citation-dense and (b) equipped with aligned, human-written gold summaries.
The March 2026 plan split these across five corpora — the citation-dense ones
had no summaries (UK Legislation, EUR-Lex raw, eCFR), the summary-bearing ones
were citation-poor (BillSum, GovReport). That design would have reproduced the
ObliQA null by construction.

Phase 1's completion also removes the March plan's entire "Problem 1" track:
extraction correctness is solved (0.957 recall / 0.980 audited precision on a
sealed test; transfers to new domains untouched). Phase 3 therefore needs
exactly **one** corpus, chosen by this gate.

## 2. Candidates (revised after Tuba's suggestions, July 2026)

| # | Dataset | Gold summaries | Citation density | Status |
|---|---|---|---|---|
| **C1** | **EUR-Lex-Sum** (Aumiller et al., EMNLP 2022; CC-BY-SA 4.0) | ✅ human-written, aligned | **measured: 16.3 mentions/1k words** | **Leading candidate — G1 passed** |
| C2 | ReguSum (SEC/IRS, internal to the group) | ✅ reported | unknown | blocked: needs access + specs |
| C3 | Department private set | unknown | unknown | blocked: specs never provided |
| C4 | BillSum (US bills + summaries) | ✅ | moderate (per March audit) | keep as **low-linkage control** |
| C5 | Multi-LexSum (Tuba's suggestion) | ✅ | n/a | deferred — multi-document is a different problem |
| C6 | Australian Legal Case Reports (Tuba's suggestion) | ❌ (citation-rich, no summaries) | high | deferred — case law, and no gold summaries |
| — | UK Legislation + Explanatory Notes | ⚠️ see below | high | **not recommended as gold** |
| — | eCFR, GovReport | ❌ / ✅ but citation-poor | — | retired |

**On UK Explanatory Notes** (Tuba's Email 3, and the March plan's own
position): extraction would work — section/Schedule references are as regular
as EU ones. The objection is to using the Notes as *gold summaries*. They
explain rather than condense: they carry policy background and legislative
intent, have no fixed compression ratio, and are frequently as long as or
longer than the provisions they describe. Scoring a compressive summariser
against them measures the wrong thing. The March deck reached the same
conclusion independently. Recommend: not as gold; potentially useful later as
auxiliary explanatory signal.

**Key finding — no dataset construction is required.** Tuba's Email 4 concluded
that no existing dataset has both the graph structure and prepared summaries,
implying we must build one from EUR-Lex or legislation.gov.uk. The missing half
is the *graph*, and the graph is what this project already builds. EUR-Lex-Sum
supplies the document–summary pairing (packaged, licensed, citable); we add the
citation layer. This removes the scraping programme from the plan entirely.

## 3. Gate metrics

All computed with the **frozen Phase-1 extractor, zero retuning** (the CUAD
protocol: only a corpus-specific ingest may be written; detection and
resolution stay untouched). No LLM calls anywhere in the gate study.

**G1 — Citation density and resolvability.** ✅ **MEASURED (density); resolution OPEN**
- mentions per 1,000 words; documents with zero mentions
- resolution rate (% of mentions resolved to a passage), edges per document

**G2 — Summary–citation linkage (the decisive gate).** ⏳ **PROXY ONLY so far**
Align each gold-summary sentence to its supporting source passage(s), TWO ways,
reporting both and their agreement:
- lexical: ROUGE-2/L overlap, top-m passages per summary sentence
- semantic: bge-small embedding similarity, top-m per summary sentence

Then:
- **G2a (static linkage):** fraction of summary-supporting passages that share
  a citation edge with another supporting passage. Anchors: CUAD gold spans
  51.2% citing (gate passed); ObliQA evidence pairs 0.5% (gate failed).
- **G2b (rescueability at the usable frontier):** simulate the content
  selection a budgeted summariser would run (top-k passages at the real token
  budget); of the summary-supporting passages it MISSES, what fraction is
  1-hop citation-reachable from those selected? This is the CUAD rescue-arm
  lesson applied to summarisation.

**G3 — Centrality predicts summary-worthiness.** ⏳ not started
Does a passage's centrality (in-degree, PageRank in its document graph) predict
whether the gold summary draws on it? Report AUC against two baselines that
must be beaten: **position (lead bias)** and **length**. If centrality adds
nothing over lead+length, PACB's budgeting premise fails on that corpus.

## 4. Results so far — EUR-Lex-Sum (Stage 1)

Full detail in `phase3/reports/eurlexsum_gate.md`. English subset: 1,504
documents (train 1,129 / validation 187 / test 188); probe run on validation.

| Measure | Result | Reading |
|---|---|---|
| **G1 density** | **16.3 mentions/1k words** (median); **0/187** empty | **PASS** — denser than CUAD's 11.6, which worked |
| Cross-document signal | median **8** instruments cited/doc; **185/187** cite ≥1 | abundant; this is the variant-B class |
| **G2 proxy** | **184/187** summaries cite another instrument (median 4); only 53/187 name a specific Article | promising, at the *instrument* (cross-document) level |
| Citation closure | **38.6%** of citations resolve inside the dataset; **704/1,023** docs have ≥1 in-corpus target | can start with **no scraping** |
| Compression | median **~13:1** (13,207 → 926 words) | realistic; supersedes the March 42K→150 assumption |

**Settled:** the extractor transfers to EU legal text untouched; the corpus is
citation-dense; gold summaries are human-written, licensed and citable;
compression is realistic; no construction needed to begin.

**Not settled:** G2 proper (a summary *mentioning* an instrument does not prove
its *content* came from there — the proxy is a precondition, not the gate);
**resolution** as distinct from detection (EU acts need an ingest that segments
into Articles plus a CELEX-based instrument router — easier than ADGM's
informal aliases, but unbuilt); and G3.

## 5. Remaining procedure

1. **Ingest** (EUR-Lex-Sum): segment acts into Articles/paragraphs via
   `ids.canon`, as `cuad_ingest.py` did for contracts; add a CELEX-based router
   so "Regulation (EU) 2016/679" resolves to a document. Measure resolution
   rate to close out G1.
2. **Pilot & freeze:** run G2/G3 on 5 documents to fix alignment parameters
   (m, similarity threshold) and sanity-check the ingest; then **freeze
   thresholds in writing** before the main run.
3. **Main run:** 30–50 documents (size-stratified); compute G2a, G2b, G3;
   write `phase3/reports/dataset_gate.md`.
4. **Decide** by the rule in §6, and take the result to the supervisor.

Cost: local compute only; zero LLM calls; ~1 week including the ingest.

## 6. Thresholds and decision rule

Provisional; to be **frozen after the pilot, before the main run** (the pilot
may recalibrate alignment mechanics, not the bar's spirit):

- **PASS G1:** ≥ 5 mentions/1k words AND ≥ 25% resolution
  — density already passed (16.3); resolution outstanding
- **PASS G2:** G2a ≥ 25% under BOTH alignment methods, AND G2b ≥ 15% at the
  frozen frontier (ObliQA 0.5% and CUAD 3.2% frame the floor; a summarisation
  corpus must sit well above the CUAD-marginal regime, because Phase 3 has no
  rescue-arm escape hatch)
- **PASS G3:** centrality AUC beats the lead+length baseline

**Decision rule:** adopt C1 (EUR-Lex-Sum) if it passes G1 and G2. G3 failing
does not veto adoption but removes PACB-style centrality budgeting from the
Phase 3 design (graph-based content selection remains). C2/C3 are only
assessable if access materialises. C4 (BillSum) is measured but not adoptable
as primary: it serves as the **low-linkage control** where the method is
*predicted* to gain little — confirming that prediction is itself evidence for
the gate methodology.

**If EUR-Lex-Sum fails G2:** report it (the gate working as designed) and
pivot to the fallback — a small citation-dependent summarisation evaluation
built on the ADGM corpus, where 90% linkage is already proven — scope to be
agreed with the supervisor first.

## 7. The experiment this enables (Tuba's design)

Recorded here because it shapes what the gate must prove. Tuba's proposed
comparison, which matches the Phase 2 base/graph contrast exactly:

1. summarise from the **focal document alone**
2. summarise from the **focal document + graph-retrieved cited material**

This is context augmentation, not reranking — consistent with Phase 2's
conclusion that the graph must be used to *augment context, never to rerank*.
The G2b measurement is precisely the precondition for (2) to differ from (1).

## 8. Risks

- **Alignment noise (biggest):** G2/G3 depend on summary→passage alignment;
  hence two independent methods, agreement reported, pilot calibration. Wild
  disagreement ⇒ mark the numbers low-confidence rather than average them.
- **EUR-Lex-Sum summary style:** the EU summaries are written for citizens and
  include context with no source passage. Report alignment *coverage* (% of
  summary sentences aligning to anything) so this dilution is visible.
- **Instrument-level vs Article-level linkage:** the proxy suggests summaries
  engage at instrument level. If G2 confirms this, the unit of graph retrieval
  may need to be a whole cited act rather than a passage — a design
  consequence worth anticipating.
- **Only 39% citation closure:** experiments restricted to in-corpus targets
  may be biased toward heavily-cited instruments. Report this population
  characteristic rather than treating the 704 documents as a random sample.
- **C2/C3 access** remains an open ask to the group.

## 9. Timeline note (added August 2026)

The presentation is mid-August and the dissertation is due in September. The
dataset question is now cheap and largely answered, but Phase 3 proper (ingest,
resolution, gate, then the summarisation experiments) remains a substantial
programme. Tuba has explicitly offered the alternative of strengthening the
existing work. Recommended sequencing: complete the gate (≈1 week, no LLM
cost), then decide with the supervisor whether to run the full study or to
consolidate Phases 1–2 for the dissertation.

## 10. Out of scope

The summarisation method itself (RCGC/PACB or successor), compression sweeps,
any LLM generation, and any RePASs-style evaluation design. Those are Phase 3
proper, gated on this plan's outcome and supervisor approval. The
already-identified method fixes (compression sweep instead of a fixed ratio;
soft reference-closure; centrality validated before budgeting) are recorded in
CLAUDE.md §8 and unchanged.
