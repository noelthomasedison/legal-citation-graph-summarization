# When Do Citation Graphs Help Legal Language Models?

MSc dissertation - Noel Thomas Edison, MSc AI & Machine Learning, University
of Birmingham.

Legal texts are connected instruments, but language models usually receive
isolated chunks. A rule may state that a report is due within the period in a
different article; without following that citation, the model knows a deadline
exists but not what it is.

This dissertation tests one claim across extraction, retrieval, retrieval-
augmented generation (RAG), and long-document summarisation:

> A citation graph is useful only when missing task evidence is
> **citation-linked, reachable, and usable by the downstream task**.

The graph is therefore not treated as automatically beneficial. The experiments
measure when it can deliver missing evidence, when that evidence changes an
answer, and when additional cited context merely consumes a fixed context
budget.

## Research design

The work follows one auditable pipeline:

1. **Segment** legal documents into structural passages.
2. **Detect** explicit reference mentions with rules.
3. **Resolve** each mention to a passage or legal act.
4. **Assemble** the directed citation graph.
5. Test the graph in three downstream roles: extraction, retrieval/RAG, and
   summarisation.

The downstream experiments use controlled conditions:

| Condition | Evidence available |
|---|---|
| **Base** | No graph augmentation |
| **Variant A** | Base plus within-document citation evidence |
| **Variant B** | Variant A plus cross-document citation evidence |
| **Oracle** | Gold-selected diagnostic upper bound; not a deployable system |

ADGM was the starting corpus. Later phases use ObliQA, ObliQA-XRef, CUAD and
EUR-Lex-Sum to test downstream value and generalisation.

| Phase | Corpus / benchmark | Purpose |
|---|---|---|
| **1** | 40 ADGM rulebooks; 13,732 passages | Build and evaluate automatic cross-reference extraction |
| **2** | ObliQA, ObliQA-XRef and CUAD | Test retrieval reranking and RAG context augmentation |
| **3** | 80 EUR-Lex-Sum test acts | Test citation-aware long-document summarisation |

## Phase 1 - automatic citation extraction

Detection and resolution remain separate so that errors can be inspected. The
rule grammar was tuned only on the labelled development split; no learned model
was trained for extraction. The evaluator and thresholds were fixed before the
held-out test set was opened.

| Metric | Observed | Pre-registered gate | Result |
|---|---:|---:|---|
| Internal-reference recall | **95.7%** | >= 90% | Pass |
| Overall recall | **82.5%** | >= 80% | Pass |
| Cross-document recall | **74.3%** | >= 45% | Pass |
| Human-audited precision | **98.0%** | >= 80% | Pass |

All four gates passed. Manual auditing was essential because the supplied gold
cross-reference resource is high precision but non-exhaustive: valid new edges
can appear to be false positives when compared with gold alone. The extractor
can therefore propose valid extensions to the group's resource.

Evidence: [`step6_test_run.md`](phase1/reports/step6_test_run.md) and
[`test_audit_results.md`](phase1/reports/test_audit_results.md).

## Phase 2 - retrieval and RAG

The graph was tested with two different operators:

- **Retrieval reranking:** propagate graph scores and change candidate order.
- **RAG context augmentation:** preserve the baseline ranking and add cited
  targets to the answer prompt.

### Retrieval

| Benchmark | Base | Variant A | Variant B | Interpretation |
|---|---:|---:|---:|---|
| ObliQA Recall@10 | 76.5% | 75.7% | 75.5% | Only 0.5% of gold evidence pairs are citation-linked; no gain |
| ObliQA-XRef target Recall@1 | 41.5% | 60.6% | 63.8% | **+22.3 percentage points** for B over Base |
| CUAD rerank Recall@1 | 38.8% | 24.8% | N/A | Reranking hurt at every reported cutoff |

CUAD has no cross-contract condition because contracts do not cite one another;
its graph condition is Variant A, using within-contract references only.

### Answer faithfulness

RePASs combines entailment score (ES), contradiction score (CS), and obligation
coverage (OC): `RePASs = (OC + ES - CS + 1) / 3`.

| Population | Base | Graph | Oracle | Graph - Base |
|---|---:|---:|---:|---:|
| ObliQA, all 300 questions | 37.1 | 36.9 | - | -0.2 pp |
| CUAD, all 150 questions | 31.1 | 31.0 | 33.8 | -0.05 pp |
| ObliQA-XRef, 16 rescued questions | 31.8 | 34.0 | 35.7 | +2.1 pp |
| CUAD, 100-question rescue arm | 23.3 | 32.6 | 33.3 | **+9.3 pp** |

For the CUAD rescue arm, the paired Wilcoxon test gives
`p = 1.8 x 10^-7`. This is strong evidence that the improvement is not random
within that deliberately selected rescue population. It is not evidence of a
general improvement over all CUAD questions: augmentation was null on the full,
unselected set.

The Phase 2 lesson is therefore conditional: graph evidence helps when the
baseline misses evidence and the graph can supply it. Context augmentation is
the safer operator in this setting because it retains strong baseline
candidates; CUAD graph reranking instead displaced them.

Evidence: [`xref_retrieval.md`](phase2/reports/xref_retrieval.md),
[`cuad_retrieval.md`](phase2/reports/cuad_retrieval.md), and
[`cuad_rescue_repass.md`](phase2/reports/cuad_rescue_repass.md).

## Phase 3 - EUR-Lex summarisation

Phase 3 tested two summarisation methods under Base/A/B/Oracle conditions:

1. **Historical single-pass v1:** selected focal passages and raw cited
   provisions were passed directly to one final summarisation call. Later audit
   found irrelevant target material and imperfectly controlled contexts, so
   these results are retained as historical diagnostics.
2. **Hierarchical v2 (authoritative):** a repaired and audited EUR-Lex graph,
   exactly controlled prompt budgets, citation-conditioned evidence cards,
   four document-order group briefs, and a final composition stage. Unsupported
   cards abstain and never fall back to raw target text. Cross-document evidence
   displaces Base content, so treatment prompts never grow beyond their
   comparator.

The final experiment generated **320 summaries**: 80 acts x four conditions.
Variant B delivered cross-document evidence in 36/80 acts, 33 comparisons were
balanced and genuinely treated, but only **two acts** contained clean,
summary-essential incremental cross-document rescues. Strict H1 is therefore
underpowered and remains untested rather than refuted.

### Automatic summary metrics (scores x100)

| Method | Metric | Base | A | B | Oracle |
|---|---|---:|---:|---:|---:|
| v1 single-pass | ROUGE-1 | 41.79 | 41.46 | 41.91 | 41.50 |
|  | ROUGE-2 | 15.88 | 16.39 | 16.29 | 16.75 |
|  | ROUGE-L | 20.22 | 20.22 | 20.40 | 20.63 |
|  | BERTScore-F1 | 83.70 | 83.88 | 83.85 | 84.12 |
| **v2 hierarchical** | **ROUGE-1** | **42.83** | **43.68** | **44.00** | **44.81** |
|  | ROUGE-2 | 15.45 | 16.12 | 16.05 | 17.45 |
|  | ROUGE-L | 19.35 | 19.63 | 19.70 | 20.64 |
|  | BERTScore-F1 | 83.42 | 83.47 | 83.42 | 83.79 |

### Blinded LLM judge (normalised 0-100)

| Perspective | Base | A | B | Oracle |
|---|---:|---:|---:|---:|
| User-facing summary | 56.5 | 55.3 | 54.5 | 63.3 |
| Legal meaning represented in gold | 59.7 | 60.0 | 59.5 | 66.5 |

No statistically detectable Base-to-A or A-to-B improvement was observed.
Oracle exceeded Base by 6.8 points on the normalised scale, equivalent to
`+0.338` on the original 1-5 scale, for both judge perspectives
(`p = 0.0008` user; `p = 0.0011` legal). This only demonstrates that the
evaluation can detect better evidence: Oracle uses gold information during
selection and is not a deployable comparison.

Further limitations are explicit:

- EUR-Lex-Sum gold summaries are public-facing and may omit legal detail.
- The blinded judge measures legal meaning represented in the gold; it cannot
  verify extra candidate detail without the source act.
- RePASs was not used for authoritative v2 because it is not validated for
  abstractive EUR-Lex summarisation.
- The 74.3% cross-document recall is a held-out ADGM result, not a measured
  EUR-Lex recall value.

Evidence:
[`summarisation_hier_v2_citation_card_full_v4.md`](phase3/reports/summarisation_hier_v2_citation_card_full_v4.md)
and
[`llm_judge_hier_v2_test_citation_card_full_v4_openai_gpt_oss_120b_m8192.md`](phase3/reports/llm_judge_hier_v2_test_citation_card_full_v4_openai_gpt_oss_120b_m8192.md).

## Overall conclusion

The dissertation does not claim that citation graphs always improve legal
language models. It establishes a diagnostic explanation across three tasks:

- ObliQA: almost no usable citation path, so the graph produces no gain.
- ObliQA-XRef: citation-dependent evidence is available, so retrieval improves
  substantially.
- CUAD: graph augmentation rescues answers when baseline retrieval misses the
  evidence, but the effect is conditional and reranking can be harmful.
- EUR-Lex-Sum: the graph finds connected law, but too little of the reference
  summary depends uniquely on the recovered cross-document evidence to detect
  an A-to-B benefit with 80 acts.

The results point to **task-aware selection of graph evidence** as the missing
component. Future work should predict which citation targets are answer- or
summary-worthy and build a sufficiently powered citation-dependent
summarisation rescue set.

## Repository layout

```text
phase1/                 Phase 1 - extraction and sealed evaluation
  src/regkg/            ingest, hierarchy, detection, resolution and evaluation
  scripts/01..08        audit -> ingest -> extract -> ablate -> sealed test
  tests/                extraction regression tests
  reports/              Phase 1 evidence and audit reports
  PLAN.md               pre-registered design and amendments

phase2/                 Phase 2 - retrieval and RAG
  src/                  retrieval harness and CUAD ingestion
  scripts/01..20        ObliQA -> XRef -> CUAD -> RAG and rescue experiments
  reports/              retrieval, RePASs and statistical results

phase3/                 Phase 3 - EUR-Lex-Sum summarisation
  src/                  EUR-Lex ingestion/resolution, contexts, cards and judge
  scripts/01..11        historical v1 feasibility and single-pass experiment
  scripts/12..21        audited graph -> cards -> hierarchical generation ->
                        evaluation -> blinded judge
  tests/                graph, context, provider, cache, card and judge tests
  data/                 versioned final artefacts and manifests
  reports/              authoritative Phase 3 reports
  PHASE3_V2_HIERARCHICAL_PLAN.md
                        frozen design, amendments and interpretation rules
```

Presentation decks, PDFs, study guides and their build artifacts live outside
this repository. The repository contains code, tests, versioned experimental
artifacts and result reports.

## Reproduction

1. Create the environment:

   ```bash
   python -m venv phase1/.venv
   phase1/.venv/bin/pip install -r requirements.txt
   ```

2. Obtain the public RegNLP datasets:

   ```bash
   git clone https://github.com/RegNLP/GraphRAG4RegGraph phase1/data/raw/GraphRAG4RegGraph
   git clone https://github.com/RegNLP/ObliQADataset phase2/data/raw/ObliQADataset
   git clone https://github.com/RegNLP/ObliQA-XRef phase2/data/raw/ObliQA-XRef
   git clone https://github.com/RegNLP/RePASs phase2/data/raw/RePASs
   ```

   Download CUAD's `CUADv1.json` from the Atticus Project into
   `phase2/data/raw/CUAD/CUADv1.json`. Phase 3 downloads
   `dennlinger/eur-lex-sum` through Hugging Face Hub. Authenticate with Hugging
   Face to use the exact `meta-llama/Llama-3.3-70B-Instruct` tokenizer.

3. Train the RePASs obligation classifier:

   ```bash
   phase1/.venv/bin/python phase2/scripts/09_train_obligation_clf.py
   ```

4. Configure model access. Real keys are ignored and must never be committed:

   - NVIDIA Build: `phase1/.nvidia_api_key`
   - OpenRouter: `phase1/.openrouter_api_key`

   Phase 2 used `meta/llama-3.3-70b-instruct` through NVIDIA. The authoritative
   Phase 3 cards and summaries used OpenRouter's
   `meta-llama/llama-3.3-70b-instruct`, pinned to CoreWeave FP16 with provider
   fallbacks disabled, temperature 0, one worker and a 20-RPM launch ceiling.
   The blinded judge used `openai/gpt-oss-120b`, pinned to CoreWeave FP4.

5. Run the numbered pipelines. For Phase 3 v2, the controlled sequence is:

   ```text
   12 build graph
   16-17 sample and score the graph audit
   13 export frozen citation-card requests
   19 build verified citation cards
   13 rebuild exact-token Base/A/B/Oracle contexts from those cards
   14 generate hierarchical summaries
   15 evaluate ROUGE/BERTScore and registered contrasts
   21 run the blinded LLM judge
   ```

   Exact arguments, artifact tags and interpretation rules are recorded in
   [`PHASE3_V2_HIERARCHICAL_PLAN.md`](phase3/PHASE3_V2_HIERARCHICAL_PLAN.md)
   and the committed manifests. Every reported number traces to a versioned
   report or machine-readable result artifact.
