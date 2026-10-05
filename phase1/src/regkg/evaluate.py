"""Edge-level scoring of predicted cross-references against the gold oracle.

Pre-registered semantics (PLAN.md):
  A predicted edge (src_uid, tgt_uid) matches a gold edge iff src matches AND
  tgt equals the gold target (EXACT credit) or lies inside its nested
  expansion (NESTED credit). Both modes are reported.

Precision is prediction-side (unique predicted edges that match some gold
edge); recall is gold-side (gold edges covered by some prediction). The two
counts differ when one prediction covers several gold rows or vice versa.
"""
from __future__ import annotations

from dataclasses import dataclass

from .gold import GoldEdge


@dataclass(frozen=True)
class PredEdge:
    source_uid: str
    target_uid: str
    mention: str = ""      # surface text that produced the edge (error analysis)
    how: str = ""          # resolution provenance: exact|app-alt|suffix|
                           #   suffix-structural, +ascent, @fsmr, dup-alt, self
    keyword: str = ""      # detector keyword ("Rule", "Part", ...) or ""


@dataclass
class Scores:
    tp_pred: int           # predicted edges that matched >=1 gold edge
    matched_gold: int      # gold edges covered by >=1 prediction
    n_pred: int
    n_gold: int

    @property
    def precision(self) -> float:
        return self.tp_pred / self.n_pred if self.n_pred else 0.0

    @property
    def recall(self) -> float:
        return self.matched_gold / self.n_gold if self.n_gold else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if p + r else 0.0

    def row(self) -> str:
        return (f"P={self.precision:.3f}  R={self.recall:.3f}  F1={self.f1:.3f}   "
                f"(pred={self.n_pred}, gold={self.n_gold})")


def score(preds: list[PredEdge], gold: list[GoldEdge], nested: bool = True,
          source_kin: dict[str, set[str]] | None = None) -> Scores:
    """`source_kin` (optional): gold source uid -> set of additionally
    acceptable prediction source uids (ancestors/descendants). Motivated by
    the corpus duplicating child text inside parents while the gold mixes
    source-attachment conventions; reported as a SECONDARY credit mode."""
    gold = [g for g in gold if g.evaluable]
    uniq = {(p.source_uid, p.target_uid) for p in preds}

    by_src: dict[str, list[tuple[int, GoldEdge]]] = {}
    for i, g in enumerate(gold):
        by_src.setdefault(g.source_uid, []).append((i, g))
        for kin in (source_kin or {}).get(g.source_uid, ()):
            by_src.setdefault(kin, []).append((i, g))

    def hits(g: GoldEdge, tgt: str) -> bool:
        return tgt == g.target_uid or (nested and tgt in g.expanded_target_uids)

    matched_gold: set[int] = set()
    tp_pred = 0
    for src, tgt in uniq:
        found = False
        for i, g in by_src.get(src, []):
            if hits(g, tgt):
                matched_gold.add(i)
                found = True
        tp_pred += int(found)
    return Scores(tp_pred=tp_pred, matched_gold=len(matched_gold),
                  n_pred=len(uniq), n_gold=len(gold))


def build_source_kin(gold: list[GoldEdge], corpus) -> dict[str, set[str]]:
    """Ancestors and descendants of each gold source, for source-nested credit."""
    kin: dict[str, set[str]] = {}
    for g in gold:
        if not g.evaluable:
            continue
        src = corpus.by_uid.get(g.source_uid)
        if src is None:
            continue
        rel = set()
        for p in corpus.passages:
            if p.doc_id != src.doc_id or p.uid == src.uid:
                continue
            a, b = p.path, src.path
            if (len(a) < len(b) and b[:len(a)] == a) or \
               (len(b) < len(a) and a[:len(b)] == b):
                rel.add(p.uid)
        kin[g.source_uid] = rel
    return kin


def unmatched_gold(preds: list[PredEdge], gold: list[GoldEdge],
                   nested: bool = True) -> list[GoldEdge]:
    """Gold edges no prediction covered — the false-negative pool for error analysis."""
    gold = [g for g in gold if g.evaluable]
    uniq = {(p.source_uid, p.target_uid) for p in preds}
    by_src: dict[str, set[str]] = {}
    for src, tgt in uniq:
        by_src.setdefault(src, set()).add(tgt)
    out = []
    for g in gold:
        tgts = by_src.get(g.source_uid, set())
        if g.target_uid in tgts:
            continue
        if nested and tgts & g.expanded_target_uids:
            continue
        out.append(g)
    return out


def false_positives(preds: list[PredEdge], gold: list[GoldEdge],
                    nested: bool = True) -> list[PredEdge]:
    """Unique predictions matching no gold edge — the precision-error pool.

    NB: some of these may be gold-curation misses rather than extractor errors
    (the gold is manual); the error analysis samples and inspects them.
    """
    gold = [g for g in gold if g.evaluable]
    by_src: dict[str, list[GoldEdge]] = {}
    for g in gold:
        by_src.setdefault(g.source_uid, []).append(g)
    seen: set[tuple[str, str]] = set()
    out = []
    for p in preds:
        key = (p.source_uid, p.target_uid)
        if key in seen:
            continue
        seen.add(key)
        ok = any(p.target_uid == g.target_uid
                 or (nested and p.target_uid in g.expanded_target_uids)
                 for g in by_src.get(p.source_uid, []))
        if not ok:
            out.append(p)
    return out
