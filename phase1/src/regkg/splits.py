"""Frozen dev/test split at the document level.

Split semantics: an edge belongs to its SOURCE document's split. Rules are tuned
only on dev-doc edges; test-doc edges are scored once at the end. The extractor
may still see the whole corpus text for resolution (targets can live in any
document) — what is held out is the gold supervision, not the corpus.

Dev docs are chosen deterministically to (a) span the document-size range,
including the largest doc, and (b) carry enough outgoing gold edges to tune
recall against.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .gold import GoldEdge
from .ingest import Corpus

N_DEV = 8


def make_split(corpus: Corpus, gold: list[GoldEdge]) -> dict:
    sizes = Counter(p.doc_id for p in corpus.passages)
    edge_counts = Counter(e.source_doc for e in gold if e.evaluable)
    # docs with gold edges, largest-first; docs without edges are useless for tuning
    candidates = sorted(edge_counts, key=lambda d: -sizes[d])
    # take every k-th candidate across the size spectrum -> spans big and small
    step = max(1, len(candidates) // N_DEV)
    dev = sorted(candidates[::step][:N_DEV])
    test = sorted(d for d in corpus.doc_ids() if d not in dev)
    return {"dev_docs": dev, "test_docs": test,
            "dev_edges": sum(edge_counts[d] for d in dev),
            "test_edges": sum(edge_counts[d] for d in test)}


def save_split(split: dict, path: Path) -> None:
    if path.exists():
        frozen = json.loads(path.read_text())
        if frozen["dev_docs"] != split["dev_docs"]:
            raise RuntimeError(
                f"split already frozen at {path}; refusing to overwrite")
        return
    path.write_text(json.dumps(split, indent=2) + "\n")
