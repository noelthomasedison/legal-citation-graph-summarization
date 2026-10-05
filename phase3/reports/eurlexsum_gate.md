# Phase 3 dataset gate — EUR-Lex-Sum (feasibility probe)

Frozen Phase-1 detector, **zero retuning** (the protocol that carried
the ADGM extractor to CUAD). Source: EUR-Lex-Sum (Aumiller et al.,
EMNLP 2022), English subset, CC-BY-SA 4.0. No LLM calls.

Corpus: **1504 English documents** (train 1129, validation 187, test 188); probe run on the 187 validation documents.

## Shape

- document length (words): median 13207.0, mean 18702.7, max 209999
- summary length (words): median 926.0, mean 1011.8, max 5199
- compression (summary/document): median 0.074 (~13:1)

## G1 — detection (does the extractor fire?)

- mentions per 1,000 words: **median 16.3, mean 18.6, max 100**
- documents with zero mentions: **0/187**
- anchors: CUAD 11.6 per 1,000 words (gate passed, mechanism worked);
  ADGM is the corpus the rules were tuned on.
- **verdict: PASS** — higher density than CUAD, and no document is empty.

## EXT — cross-document signal (variant B)

- distinct other instruments cited per document: median 8.0, mean 11.5, max 50
- documents citing >= 1 other instrument: **185/187**
- this is the *external* reference class — Phase 1's weakest (recall 0.743) but the class ObliQA-XRef showed carries the value.

## G2 (PROXY ONLY) — do summaries engage with cited material?

- summaries citing another instrument: **184/187** (median 4.0, mean 5.4, max 81)
- summaries naming a specific 'Article N': 53/187 (median 0.0, mean 0.8, max 27)

Reading: the summaries operate at the **instrument** level (cross-document) far more than the article level. That matches the
experiment Tuba proposed — focal document alone vs focal document +
graph-retrieved cited material — and it is the cross-document case.

> **This is a precondition, not the gate.** A summary *mentioning* > Directive 95/46/EC does not prove its *content* came from that > instrument. True G2 requires the two-way alignment in > `DATASET_PLAN.md` §3 and is NOT established here.

## CLOS — is the corpus closed under citation?

- distinct cited instruments (summed over documents): 7,861
- of those, present in EUR-Lex-Sum itself: **3,035 (38.6%)**
- per-document coverage: median 33%, mean 35%
- documents with >= 1 cited instrument also in corpus: **704/1023**

Reading: roughly a third of citations resolve *inside* the dataset, so
a first experiment needs **no scraping at all** — there is already a
large population where a citation can be followed to a document we
hold. Fuller coverage is programmatic (CELEX ids give stable URLs),
but is an optional extension rather than a prerequisite.

## What this settles, and what it does not

SETTLED: the extractor transfers to EU legal text untouched; the corpus is citation-dense; gold summaries exist, are human-written, licensed (CC-BY-SA 4.0) and citable; compression is realistic (~13:1, not the 42K->150 ratio the March plan assumed); and no dataset construction is required to begin.

OPEN: true G2 (does cited *content* reach the summary), resolution rate of EU-style references (detection != resolution — needs an ingest that segments acts into Articles and an instrument-id router), and G3 (does centrality predict summary-worthiness).
