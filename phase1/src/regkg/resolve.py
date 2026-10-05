"""Resolve detected mentions to target passages.

Per mention:
  1. Build candidate component tuples from the core token + keyword.
     Structural keywords fuse with the number ("Part 4" -> ("part 4",))
     because corpus paths store them as one component; numeric keywords
     (Rule/Section/...) resolve by number ("3.1.4(2)(b)" -> ("3","1","4","2","b")).
  2. Target document: nearest alias in a window around the mention wins
     ("... of the FSMR"); otherwise the source document.
  3. Lookup ladder: exact path -> appendix alt spelling -> FULL-tuple suffix
     (never a sub-suffix: that mis-resolved 2.2.1(2) to 2.1.2 in v1) ->
     leaf ascent (drop trailing components down to length 2, retrying; the
     gold often points at 10.3.2.1 when the text cites 10.3.2(1)(b)).
  4. Ranges expand numerically on the final component over a shared prefix.

Attribution: parent passages duplicate child text in this corpus, so a
mention is credited to the DEEPEST passage whose text contains it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .detect import Mention, detect
from .evaluate import PredEdge
from .ingest import Corpus, Passage
from .textutil import clean

_PAREN = re.compile(r"\(([a-zA-Z0-9]+)\)")
_APP = re.compile(r"^A(?:PP)?\s?(\d+)$", re.IGNORECASE)
# keywords whose corpus paths fuse keyword+number into one component
_FUSED = {"part": "part", "parts": "part",
          "chapter": "chapter", "chapters": "chapter",
          "schedule": "schedule", "schedules": "schedule",
          "app": "app", "appendix": "app"}
MAX_SUFFIX = 4
ALIAS_WINDOW = 80


def parse_core(core: str) -> tuple[str, ...]:
    comps: list[str] = []
    for seg in core.split("."):
        seg = seg.strip()
        if not seg:
            continue
        parens = _PAREN.findall(seg)
        head = _PAREN.sub("", seg).strip()
        m = _APP.match(head)
        if m and not comps:
            comps.append(f"app{m.group(1)}")
        elif head:
            comps.append(head.lower())
        comps.extend(p.lower() for p in parens)
    return tuple(comps)


def candidate_tuples(core: str, keyword: str | None) -> list[tuple[str, ...]]:
    cands = []
    kw = (keyword or "").lower()
    fused = _FUSED.get(kw)
    if fused and re.fullmatch(r"\d+[A-Z]?", core, re.IGNORECASE):
        if fused == "app":
            cands.append((f"app{core.lower()}",))
        else:
            cands.append((f"{fused} {core.lower()}",))
    parsed = parse_core(core)
    if parsed and parsed not in cands:
        cands.append(parsed)
    return cands


class SuffixIndex:
    def __init__(self, corpus: Corpus):
        self.idx: dict[tuple[int, tuple[str, ...]], list[Passage]] = {}
        for p in corpus.passages:
            for k in range(1, min(MAX_SUFFIX, len(p.path)) + 1):
                self.idx.setdefault((p.doc_id, p.path[-k:]), []).append(p)

    def lookup(self, doc_id: int, comps: tuple[str, ...]) -> list[Passage]:
        return self.idx.get((doc_id, comps), [])


@dataclass
class Resolver:
    corpus: Corpus
    aliases: dict[str, int]
    alias_re: re.Pattern
    # ablation flags — defaults reproduce the full system (rungs 2..6)
    use_guards: bool = True        # rung 2: semantic precision guards
    use_aliases: bool = True       # rung 3: alias routing (docmap)
    use_fsmr: bool = True          # rung 4: FSMR fallback for statute mentions
    use_tolerant: bool = True      # rung 5: suffix match + leaf ascent
    use_attribution: bool = True   # rung 6: deepest-container attribution
    suffix: SuffixIndex = field(init=False)
    n_ambiguous: int = 0
    n_unresolved: int = 0
    unresolved_samples: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.suffix = SuffixIndex(self.corpus)
        # FSMR is the framework law the rulebooks cite; statute-style mentions
        # that fail in the picked doc are retried there (dev-tuned heuristic)
        self.fsmr_doc: int | None = self.aliases.get("fsmr")

    # ------------------------------------------------------------------
    _NOT_A_DOC = {"app", "appendix", "rule", "rules", "section", "sections",
                  "chapter", "chapters", "part", "parts", "schedule", "schedules"}

    def _target_doc(self, text: str, m: Mention, source_doc: int) -> tuple[int, str]:
        """Structured alias forms only. Returns (doc_id, kind):
        kind = "explicit" (alias pinned the doc), "default" (source doc),
        or "unknown" ("of the PRMS Guidelines" — names a document outside the
        corpus/alias table; the mention must NOT be force-resolved).
        """
        if not self.use_aliases:
            return source_doc, "default"
        head = text[max(0, m.start - 24): m.start]
        last = None
        for last in self.alias_re.finditer(head):
            pass
        if last is not None and head[last.end():].strip() == "":
            return self.aliases[last.group(1).lower()], "explicit"

        tail = text[m.end: m.end + 40]
        post = re.match(r"\s*(?:\([^)]{0,40}\)\s*)?(?:of|under|in)\s+(?:the\s+)?",
                        tail)
        if post:
            a = self.alias_re.match(tail, post.end())
            if a:
                return self.aliases[a.group(1).lower()], "explicit"
            nxt = re.match(r"[A-Z][A-Za-z]{2,}", tail[post.end():])
            if nxt and nxt.group(0).lower() not in self._NOT_A_DOC:
                return source_doc, "unknown"
        return source_doc, "default"

    def _try(self, doc_id: int, comps: tuple[str, ...]) -> tuple[Passage | None, str]:
        """Exact path, appendix alt spelling, then full-tuple suffix."""
        if not comps:
            return None, ""
        hit = self.corpus.by_path.get((doc_id, comps))
        if hit:
            return hit[0], "exact"
        if comps[0].startswith("app"):
            alt = (comps[0], f"a{comps[0][3:]}") + comps[1:]
            hit = self.corpus.by_path.get((doc_id, alt))
            if hit:
                return hit[0], "app-alt"
        if self.use_tolerant and len(comps) <= MAX_SUFFIX:
            cands = self.suffix.lookup(doc_id, comps)
            if len(cands) == 1:
                return cands[0], "suffix"
            if len(cands) > 1:
                # statute disambiguation: prefer the true section node — the
                # one sitting directly under a Part/Chapter/Schedule component
                # (paragraph leaves like ".(39)" also end in the same digits)
                structural = [c for c in cands
                              if len(c.path) > len(comps)
                              and c.path[-len(comps) - 1].split(" ")[0]
                              in ("part", "chapter", "schedule")]
                if len(structural) == 1:
                    return structural[0], "suffix-structural"
                self.n_ambiguous += 1
        return None, ""

    def _lookup(self, doc_id: int, comps: tuple[str, ...]) -> tuple[Passage | None, str]:
        ascended = False
        while True:
            p, how = self._try(doc_id, comps)
            if p is not None:
                return p, (how + "+ascent" if ascended else how)
            if not self.use_tolerant:
                return None, ""            # rung <5: exact/app-alt only, no ascent
            if len(comps) <= 2:            # ascent floor: never resolve to a bare "2"
                return None, ""
            comps = comps[:-1]             # leaf ascent: 10.3.2.(1).(b) -> 10.3.2.(1)
            ascended = True

    # ------------------------------------------------------------------
    def resolve_passage(self, p: Passage, text: str | None = None) -> list[PredEdge]:
        text = clean(p.text) if text is None else text
        edges: list[PredEdge] = []
        for m in detect(text, self.alias_re if self.use_aliases else None,
                        guards=self.use_guards):
            edges.extend(self._resolve_mention(p, text, m))
        return edges

    @staticmethod
    def _expand_range(start: str, end: str) -> list[str]:
        s, e = parse_core(start), parse_core(end)
        out = [end]
        if len(s) == len(e) and s[:-1] == e[:-1] and s[-1].isdigit() and e[-1].isdigit():
            prefix = start.rsplit(s[-1], 1)[0]
            for n in range(int(s[-1]) + 1, int(e[-1])):
                out.append(prefix + str(n))
        return out

    # ------------------------------------------------------------------
    def run(self, passages: list[Passage]) -> list[PredEdge]:
        """Extract with deepest-container attribution.

        Parent passages in this corpus duplicate their children's text, so the
        same mention surfaces in both. A mention in passage p is dropped when a
        descendant of p also contains it — the deepest holder keeps the edge.
        """
        cleaned = {p.uid: clean(p.text) for p in passages}
        by_doc: dict[int, list[Passage]] = {}
        for p in passages:
            by_doc.setdefault(p.doc_id, []).append(p)

        alias_re = self.alias_re if self.use_aliases else None
        edges: list[PredEdge] = []
        for p in passages:
            descendants = [q for q in by_doc[p.doc_id]
                           if len(q.path) > len(p.path)
                           and q.path[: len(p.path)] == p.path] \
                if self.use_attribution else []
            for m in detect(cleaned[p.uid], alias_re, guards=self.use_guards):
                if any(m.text in cleaned[q.uid] for q in descendants):
                    continue               # a deeper passage owns this mention
                edges.extend(self._resolve_mention(p, cleaned[p.uid], m))
        return edges

    _HEADING_ECHO = re.compile(r"(?:PART|CHAPTER|SECTION|SCHEDULE)\s+\d", re.IGNORECASE)

    def _resolve_mention(self, p: Passage, text: str, m: Mention) -> list[PredEdge]:
        edges = []
        doc, kind = self._target_doc(text, m, p.doc_id)
        if kind == "unknown":
            return []          # names a document outside the corpus (e.g. PRMS)
        if (self.use_guards and m.start == 0 and self._HEADING_ECHO.match(m.text)
                and re.match(r"\s*[–—-]", text[m.end: m.end + 3])):
            return []          # "PART 4 – Calculating ..." is the passage's own heading
        cores = [m.core] + (self._expand_range(m.core, m.range_end) if m.range_end else [])
        kw = (m.keyword or "").lower().rstrip("s")
        statute_kw = kw in ("section", "part", "chapter", "schedule")
        docs = [doc]
        if (self.use_fsmr and statute_kw and kind != "explicit"
                and self.fsmr_doc and doc != self.fsmr_doc):
            docs.append(self.fsmr_doc)
        # ordering by keyword semantics (dev-tuned):
        #  part/schedule: candidate-major — the fused tuple must win in ANY doc
        #    before the bare number ("Part 4" ≠ rulebook chapter "4";
        #    "Schedule 1" ≠ passage "1")
        #  chapter/section & everything else: doc-major — same-doc numbering
        #    wins before the FSMR fallback ("Chapter 5" = PRU's own chapter 5)
        candidate_major = kw in ("part", "schedule") and kind != "explicit"
        for core in cores:
            tgt, how = None, ""
            cands = candidate_tuples(core, m.keyword)
            order = ([(c, d) for c in cands for d in docs] if candidate_major
                     else [(c, d) for d in docs for c in cands])
            for comps, d in order:
                tgt, how = self._lookup(d, comps)
                if tgt is not None:
                    if d != doc:
                        how += "@fsmr"
                    break
            if tgt is None:
                self.n_unresolved += 1
                if len(self.unresolved_samples) < 200:
                    self.unresolved_samples.append(f"doc{p.doc_id} `{m.text}`")
                continue
            if tgt.uid == p.uid:
                # duplicate-path pairs: the corpus holds e.g. "10.3.2.(4)" AND
                # "10.3.2.4" as distinct records on one canonical path, and the
                # gold links them; prefer the sibling record over dropping
                alt = [q for q in self.corpus.by_path.get((tgt.doc_id, tgt.path), [])
                       if q.uid != p.uid]
                if alt:
                    tgt, how = alt[0], how + "+dup-alt"
                elif comps != p.path:
                    continue               # incidental self-hit, not a citation
                else:
                    how += "+self"         # passage citing its own number
            edges.append(PredEdge(p.uid, tgt.uid, mention=m.text,
                                  how=how, keyword=m.keyword or ""))
        return edges
