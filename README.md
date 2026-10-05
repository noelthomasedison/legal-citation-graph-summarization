# Legal Summarisation RAG Research

This standalone research repository studies retrieval-augmented generation
inside a hierarchical legal summarisation pipeline.

The project preserves the existing two-stage summarisation method and tests
whether external evidence selected through semantic retrieval, verified legal
citations, or both improves summaries produced by T5, BART, and PEGASUS.

## Scope

Included from the source project:

- `phase1/`: citation extraction and graph components;
- `phase3/`: the existing hierarchical summarisation experiment; and
- the committed dependency specification.

Intentionally excluded:

- `phase2/` in its entirety, because it implements a different
  question-answering/retrieval study;
- uncommitted files from the source worktree; and
- generated datasets, caches, secrets, and presentation/report files.

The imported source snapshot is commit
`2df2261b6bc01fde25625e9ce38b4556efc75464`. The original project overview is
preserved as `SOURCE_PROJECT_README.md`.

## Current state

The repository is in the planning stage. No summarisation-RAG implementation or
new experimental result is claimed yet.

Read these files before implementation:

1. `CLAUDE.md` - research constraints, fixed decisions, validity controls, and
   running decision log.
2. `RAG_SUMMARISER_PLAN.md` - proposed pipeline, experimental conditions,
   gates, and implementation sequence.

## Core design

```text
unchanged four-group hierarchical summariser
        +
semantic and/or citation-guided retrieval evidence
        =
retrieval-augmented legal summarisation experiment
```

HDBSCAN is not part of the current design. The Phase 2 RAG code is not used.

## Reproducibility policy

- Index only the frozen training/index split.
- Never use gold summaries as retrieval queries.
- Match prompt budgets within each model and condition.
- Cache retrieval and generation outputs with content hashes.
- Record complete run manifests.
- Pilot before launching complete generation.

Run instructions will be added after the baseline adapter and tests are
implemented.
