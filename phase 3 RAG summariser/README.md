# Phase 3 RAG Summariser

This directory is the dedicated implementation area for retrieval-augmented
legal summarisation.

## Boundary

All new code, tests, configurations, retrieval indexes, manifests, and reports
for the summarisation-RAG study belong here.

Do not implement this work inside:

- `phase2/`, which is intentionally absent and belonged to a different
  question-answering study; or
- the imported `phase3/` tree, which is retained as the recoverable reference
  implementation of the existing summarisation method.

## Method to preserve

The implementation must retain:

1. structured passage segmentation;
2. passage embeddings and document-centroid ranking;
3. four contiguous document-order groups;
4. fixed-budget Stage-1 group briefs; and
5. Stage-2 composition of the four briefs.

Retrieval enters only after group selection and before Stage-1 generation.

## Planned structure

```text
phase 3 RAG summariser/
  README.md
  configs/                 frozen experiment configurations
  data/                    split manifests and local/generated data
  reports/                 audits and evaluation reports
  scripts/                 numbered orchestration entry points
  src/summariser_rag/      importable implementation
  tests/                   unit and integration tests
```

These subdirectories will be created when their first reviewed implementation
files are added. Empty scaffolding is intentionally avoided.

## Implementation order

1. Freeze the ReguSum split and published baseline settings.
2. Add tests for split isolation, gold-summary leakage, and token parity.
3. Adapt the unchanged baseline to ReguSum and T5, BART, and PEGASUS.
4. Build and audit the training/index-side semantic vector store.
5. Add source-query RAG.
6. Add generated-summary-query RAG.
7. Add citation-guided and hybrid retrieval only after the gates pass.

See the repository-level `CLAUDE.md` and `RAG_SUMMARISER_PLAN.md` before making
changes or running experiments.
