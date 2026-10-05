"""PARENT_OF edges: each passage's parent is its longest existing proper prefix."""
from __future__ import annotations

from .ingest import Corpus, Passage


def parent_of(corpus: Corpus, p: Passage) -> Passage | None:
    for cut in range(len(p.path) - 1, 0, -1):
        hit = corpus.by_path.get((p.doc_id, p.path[:cut]))
        if hit:
            return hit[0]
    return None


def build_edges(corpus: Corpus) -> list[tuple[str, str]]:
    """(parent_uid, child_uid) pairs across the whole corpus."""
    edges = []
    for p in corpus.passages:
        par = parent_of(corpus, p)
        if par is not None:
            edges.append((par.uid, p.uid))
    return edges
