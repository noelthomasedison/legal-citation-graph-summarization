# CLAUDE.md - Legal Summarisation RAG Research

This file is the canonical working agreement and running state record for this
repository. Read it before planning, editing code, running experiments, or
interpreting results.

## 1. Project objective

Investigate whether retrieval-augmented generation can improve an existing
hierarchical legal summarisation pipeline without changing that pipeline's core
selection, grouping, or two-stage generation method.

This project concerns **RAG inside summarisation**. It is not the Phase 2
question-answering/retrieval project from the source repository.

The primary comparison is between:

1. the unchanged hierarchical summariser;
2. the same summariser with semantic retrieval;
3. the same summariser with citation-guided retrieval; and
4. a hybrid of semantic and citation-guided retrieval, if the feasibility gates
   pass.

## 2. Repository provenance

- Imported on: 2026-10-05
- Source commit: `2df2261b6bc01fde25625e9ce38b4556efc75464`
- Source GitLab: `https://git.cs.bham.ac.uk/nxe513/regulatory-kg-project.git`
- Source GitHub: `https://github.com/noelthomasedison/legal-citation-graph-llm.git`
- Import policy: committed snapshot only
- Intentionally excluded: the complete `phase2/` tree
- Also excluded: uncommitted Phase 1 files present in the source worktree at
  import time

This is a standalone repository. Do not configure either source repository as a
push remote. A new remote may be added only after a new repository has been
created specifically for this project.

## 3. Fixed research decisions

The following decisions are fixed unless Noel and the supervisors explicitly
change them:

1. The generator families are:
   - `t5-large`
   - `facebook/bart-large-cnn`
   - `google/pegasus-xsum`
2. The existing summarisation method remains the baseline architecture.
3. Do not replace the summarisation method with HDBSCAN.
4. Do not import or reuse the Phase 2 question-answering RAG pipeline.
5. RAG may change only the evidence supplied to the existing Stage-1
   summarisation units.
6. The Stage-2 composition method remains unchanged for the controlled study.
7. ReguSum is the planned primary dataset because it supports direct comparison
   with the published baseline study. The exact released/authors' split must be
   obtained or reconstructed and then frozen before test evaluation.
8. Gold summaries must never be used as retrieval queries or retrieval labels at
   inference time.

## 4. Baseline summarisation method that must remain fixed

The controlled baseline is defined by the following operations:

1. Divide each legal document into structured passages.
2. Embed every passage.
3. Average the passage embeddings to form a document centroid.
4. Rank passages by similarity to the centroid.
5. Divide passages, independently of centroid ranking, into four approximately
   equal contiguous document-order groups.
6. Pack the highest-ranked passages within each group into the Stage-1 input
   budget.
7. Generate one brief per group.
8. Combine the four briefs in a second generation stage to produce the final
   summary.

The generator model and model-specific token ceiling may change between T5,
BART, and PEGASUS, but Base and RAG conditions must use identical settings
within each model.

Do not silently alter passage segmentation, centroid calculation, group
boundaries, passage ranking, prompts, output limits, decoding settings, or
Stage-2 composition while testing retrieval.

## 5. Where RAG enters

RAG is inserted after the existing group selection and before each Stage-1 group
brief is generated:

```text
document
  -> existing passage selection and four groups
  -> create a query for each group
  -> retrieve external evidence from the frozen index split
  -> pack focal passages plus retrieved evidence under a fixed budget
  -> existing Stage-1 group brief
  -> existing Stage-2 final summary
```

The initial retrieval modes are:

- **Source-query RAG:** query with the selected focal passages in a group.
- **Summary-query RAG:** produce a draft group brief, query with that generated
  brief, and regenerate the group brief with retrieved evidence.
- **Citation-guided retrieval:** retrieve verified cited targets associated with
  the group's source passages.
- **Hybrid retrieval:** combine semantic candidates and verified citation
  targets, then deduplicate and rank them under the same evidence budget.

These are planned conditions, not completed implementations or results.

## 6. Experimental conditions

Use explicit condition names in code, manifests, filenames, and reports:

| ID | Condition | Description |
|---|---|---|
| `base` | Existing summariser | Focal passages only |
| `rag_source` | Semantic RAG | Group source passages form the query |
| `rag_summary` | Summary-query RAG | Generated draft group brief forms the query |
| `citation_rag` | Citation-guided RAG | Verified cited targets provide evidence |
| `hybrid_rag` | Hybrid RAG | Semantic candidates plus citation targets |
| `shuffled` | Negative control | Matched evidence quantity with incorrect alignment |

Do not run the complete matrix until the baseline and retrieval pilots pass.

## 7. Non-negotiable validity controls

### Dataset isolation

- The retrieval index must contain only documents assigned to the index/train
  split.
- Held-out evaluation documents must never enter the index.
- Store and verify split document IDs in every run manifest.
- Index source documents only, never their gold summaries.

### Query isolation

- Never use a gold summary as a query.
- A summary-query condition must use a model-generated draft summary.
- Cache query text and hashes for auditability.

### Budget equality

- Count tokens with the generator's own tokenizer.
- Within each model, Base and retrieval conditions must have matched maximum
  input budgets, output budgets, prompts, and decoding parameters.
- Retrieved evidence must not produce a longer prompt in one condition.
- Record focal tokens, evidence tokens, truncation, and rejected evidence for
  every Stage-1 call.

### Retrieval comparability

- Freeze the embedding model, index, chunking, Top-K policy, and deduplication
  rules before test evaluation.
- Cache retrieval outputs by content hash.
- If shuffled evidence is used, preserve evidence count and approximate length,
  shuffle within the correct stratum, and prohibit accidental original matches.

### Reproducibility

- Every script must accept a seed where randomness exists.
- Every full run writes a manifest containing source commit, dataset hashes,
  split IDs, model revision, tokenizer revision, prompts, configuration, and
  package versions.
- Generation must be resumable and append-safe.
- Never overwrite a completed artefact without a new run tag.

## 8. Evaluation

Retain the published ReguSum metrics for direct comparison:

- ROUGE-1 F1
- ROUGE-2 F1
- ROUGE-L F1
- BERTScore F1

Add diagnostics needed for the new claim:

- paired per-document differences and bootstrap confidence intervals;
- factual consistency/faithfulness;
- legal-information coverage;
- retrieval relevance and redundancy;
- citation-target precision and availability for citation-guided conditions;
- prompt token parity and evidence displacement.

Never describe a metric difference as an improvement without paired uncertainty
and a clearly defined comparison population.

## 9. Repository layout

- `phase1/` - imported citation extraction and graph work; treat as a source of
  reusable, audited components.
- `phase3/` - imported existing EUR-Lex hierarchical summarisation experiment;
  treat as the reference implementation of the summarisation method.
- `phase 3 RAG summariser/` - the only location for new summarisation-RAG
  implementation, configurations, scripts, tests, run manifests, and reports.
- `RAG_SUMMARISER_PLAN.md` - approved architecture, gates, and implementation
  sequence for this project.
- `SOURCE_PROJECT_README.md` - original source-project README retained for
  provenance.
- `README.md` - this repository's public overview.

New implementation code must be added under the top-level
`phase 3 RAG summariser/` directory. The importable Python package will live at
`phase 3 RAG summariser/src/summariser_rag/` when implementation begins. Do not
rewrite the imported `phase3/` implementation in place. Wrap or call it so the
baseline remains recoverable and testable.

## 10. Development rules

1. Plan and test before launching paid or long-running generation.
2. Start with a two- to five-document smoke test, then a frozen pilot.
3. Add unit tests for split isolation, token parity, retrieval deduplication,
   resumability, and absence of gold-summary leakage.
4. Keep secrets in environment variables or ignored local files.
5. Never print API keys or commit credentials.
6. Do not run a full generation or evaluation job without Noel's explicit
   approval.
7. Do not import Phase 2 code merely because it is called RAG. Reimplement only
   the summarisation-specific retrieval components described here.
8. Preserve imported research artefacts. New runs require distinct filenames
   and manifests.

## 11. Current status

Status: **planning; no summarisation-RAG code has been implemented**.

Completed:

- Created a standalone snapshot without Phase 2.
- Repaired three pre-existing escaped-quote syntax errors in the imported Phase
  3 scripts `02_summary_source_alignment.py`, `06_passage_alignment.py`, and
  `08_evaluate_summaries.py`. The source repository was not modified.
- Created `phase 3 RAG summariser/` as the dedicated location for all new code.
- Fixed T5, BART, and PEGASUS as the generator families.
- Fixed the existing hierarchical summariser as the method to preserve.
- Identified source-query, summary-query, citation-guided, and hybrid retrieval
  as candidate conditions.

Next decisions:

1. Obtain the exact ReguSum 70/30 document split used in the published study.
2. Confirm whether the three generators will be tested only after ReguSum
   fine-tuning or in both pre-trained and fine-tuned states.
3. Confirm group-level retrieval as the primary query granularity.
4. Recover the exact embedding model, index settings, Top-K, and generation
   settings from the published ReguSum implementation.
5. Freeze the baseline specification before writing RAG code.

## 12. Running decision log

| Date | Decision | Reason |
|---|---|---|
| 2026-10-05 | Create a new standalone repository without Phase 2 | Keep the summarisation paper independent from the question-answering RAG work |
| 2026-10-05 | Preserve the current summarisation method | Supervisor requested retrieval be studied without changing the summariser |
| 2026-10-05 | Do not use HDBSCAN in the current experiment | Avoid changing the summarisation architecture while introducing RAG |
| 2026-10-05 | Fix T5, BART, and PEGASUS | Supervisor decision and alignment with the published ReguSum study |
| 2026-10-05 | Repair three imported escaped-quote syntax errors in the new repository only | Make the committed snapshot syntactically usable without altering the source worktree |
| 2026-10-05 | Place all new implementation under `phase 3 RAG summariser/` | Keep the imported Phase 3 baseline unchanged and make the new research code easy to audit |

Update this file whenever a decision changes the research question, experiment
matrix, data split, model configuration, or interpretation.
