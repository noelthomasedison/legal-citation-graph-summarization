"""Gold oracle: CrossReferenceData.csv -> evaluable gold edges (flat + nested-expanded).

Join strategy (validated in step 1): UID-first, canonical-path fallback.
Rows whose target joins neither way (36 rows, docs 3 & 7 — version mismatch in the
manual curation) are kept but marked non-evaluable, so the exclusion is documented
data, not silent filtering.

`Outsource` rows reference material outside the corpus: they have ReferenceText but
no in-corpus target, so they count for detection-level evaluation only.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from .ids import canon
from .ingest import Corpus, Passage


@dataclass
class GoldEdge:
    source_uid: str
    source_doc: int
    ref_text: str
    ref_type: str                       # Internal | External | Outsource
    target_uid: str | None              # None for Outsource / unjoinable
    target_doc: int | None
    target_path: tuple[str, ...] | None
    evaluable: bool                     # has an in-corpus, joinable target
    exclusion_reason: str | None = None
    expanded_target_uids: frozenset[str] = field(default_factory=frozenset)


def _join(corpus: Corpus, uid: str, doc_raw: str, pid_raw: str) -> Passage | None:
    p = corpus.by_uid.get(uid.strip())
    if p is not None:
        return p
    try:
        doc = int(doc_raw.strip())
    except (ValueError, AttributeError):
        return None
    hit = corpus.by_path.get((doc, canon(pid_raw.strip())))
    return hit[0] if hit else None


def load_gold(csv_path: Path, corpus: Corpus) -> list[GoldEdge]:
    rows = [r for r in csv.DictReader(open(csv_path, encoding="utf-8-sig"))
            if (r.get("SourceID") or "").strip()]
    edges: list[GoldEdge] = []
    seen: set[tuple] = set()
    for r in rows:
        src = _join(corpus, r["SourceID"], r.get("SourceDocumentID", ""),
                    r.get("SourcePassageID", ""))
        if src is None:
            continue  # step 1 showed source join is 100%; guard anyway
        ref_type = (r.get("ReferenceType") or "").strip()
        ref_text = (r.get("ReferenceText") or "").strip()
        tgt = None
        if ref_type != "Outsource":
            tgt = _join(corpus, (r.get("TargetID") or ""), r.get("TargetDocumentID", ""),
                        r.get("TargetPassageID", ""))
        key = (src.uid, ref_text, tgt.uid if tgt else None, ref_type)
        if key in seen:
            continue  # exact duplicate row
        seen.add(key)

        if ref_type == "Outsource":
            edges.append(GoldEdge(src.uid, src.doc_id, ref_text, ref_type,
                                  None, None, None, evaluable=False,
                                  exclusion_reason="outsource (detection-only)"))
        elif tgt is None:
            edges.append(GoldEdge(src.uid, src.doc_id, ref_text, ref_type,
                                  None, None, None, evaluable=False,
                                  exclusion_reason="target not in structured JSON"))
        else:
            expanded = frozenset(
                p.uid for p in corpus.descendants(tgt.doc_id, tgt.path))
            edges.append(GoldEdge(src.uid, src.doc_id, ref_text, ref_type,
                                  tgt.uid, tgt.doc_id, tgt.path, evaluable=True,
                                  expanded_target_uids=expanded))
    return edges
