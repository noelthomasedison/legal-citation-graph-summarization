"""Load the RegNLP structured JSON into Passage records with canonical paths.

Fragment passages ("1)", "(a)") get their full path from document order: they
attach under the most recent non-fragment passage. Consecutive fragments are
siblings under the same base.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .ids import canon, is_fragment


@dataclass
class Passage:
    uid: str
    doc_id: int
    doc_name: str
    passage_id: str                 # raw, as in the JSON
    path: tuple[str, ...]           # canonical full path
    text: str
    fragment: bool = False

    def to_json(self) -> dict:
        d = asdict(self)
        d["path"] = list(self.path)
        return d


@dataclass
class Corpus:
    passages: list[Passage] = field(default_factory=list)
    by_uid: dict[str, Passage] = field(default_factory=dict)
    # (doc_id, path) -> passages; a path can host >1 passage (rare duplicates)
    by_path: dict[tuple[int, tuple[str, ...]], list[Passage]] = field(default_factory=dict)

    def add(self, p: Passage) -> None:
        self.passages.append(p)
        self.by_uid[p.uid] = p
        self.by_path.setdefault((p.doc_id, p.path), []).append(p)

    def doc_ids(self) -> list[int]:
        return sorted({p.doc_id for p in self.passages})

    def in_doc(self, doc_id: int) -> list[Passage]:
        return [p for p in self.passages if p.doc_id == doc_id]

    def descendants(self, doc_id: int, target: tuple[str, ...]) -> list[Passage]:
        """All passages at or under `target` in `doc_id` (nested expansion)."""
        out = []
        for p in self.passages:
            if p.doc_id != doc_id:
                continue
            if p.path == target or (len(p.path) > len(target) and p.path[: len(target)] == target):
                out.append(p)
        return out


def load_corpus(json_dir: Path) -> Corpus:
    corpus = Corpus()
    for fp in sorted(json_dir.glob("*.json")):
        records = json.loads(fp.read_text())
        base: tuple[str, ...] = ()  # last non-fragment path, per document
        for r in records:
            raw_pid = str(r.get("PassageID", ""))
            frag = is_fragment(raw_pid)
            if frag:
                path = base + canon(raw_pid)
            else:
                path = canon(raw_pid)
                base = path
            corpus.add(Passage(
                uid=r.get("ID", ""),
                doc_id=int(r.get("DocumentID")),
                doc_name=fp.stem,
                passage_id=raw_pid,
                path=path,
                text=r.get("Passage", "") or "",
                fragment=frag,
            ))
    return corpus
