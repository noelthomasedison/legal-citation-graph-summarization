"""Segment EUR-Lex-Sum acts into Phase-1 Passage/Corpus structures.

EUR-Lex-Sum ships one unsegmented text blob per act, so before the frozen
Phase-1 resolver can build a graph we must recover the Article structure.
Mirrors phase2/src/cuad_ingest.py: detect headings, split on them, and reuse
`ids.canon` + Passage/Corpus UNCHANGED so the whole resolution stack (suffix
index, leaf ascent, hierarchy) transfers as-is.

EU acts are structured as:
    Article 5
    Subject matter
    1.  This Regulation lays down ...
    2.  It shall apply to ...
        (a) ...

so the natural units are Article -> numbered paragraph -> lettered point.
Paths are NUMERIC to match how the Phase-1 detector reads citations:
"Article 5(2)(a)" is detected with core "5(2)(a)", which `parse_core` turns
into ("5","2","a") — so Article 5(2)(a) must live at that path, NOT at
("article 5","2","a"). (Unlike Part/Chapter/Schedule, "Article" is not a
fused keyword in resolve._FUSED.)

Cross-document references are handled separately by CELEX matching (see
celex_edges) rather than the alias table: EU acts cite each other by a
canonical identifier, which is more reliable than ADGM's informal aliases.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PHASE1_SRC = Path(__file__).resolve().parents[2] / "phase1" / "src"
sys.path.insert(0, str(PHASE1_SRC))

from regkg.ids import canon                    # noqa: E402
from regkg.ingest import Corpus, Passage       # noqa: E402
from regkg.textutil import clean               # noqa: E402

# ---- headings -------------------------------------------------------------
# "CHAPTER I" / "CHAPTER 1" / "Chapter II — Scope". Only headings that ACTUALLY
# APPEAR are segmented: the unresolved diagnostics showed the largest failure
# class was "Chapters 50 to 63", which in trade agreements refers to Harmonised
# System TARIFF chapters, not to the act's own structure. Those must stay
# unresolved — inventing passages for them would manufacture false edges.
_CHAP = re.compile(r"(?m)^[ \t]*CHAPTER\s+([A-Z]+|\d+)\b", re.IGNORECASE)
_CHAP_LEGACY = re.compile(r"(?m)^[ \t]*CHAPTER\s+([IVXLC]+|\d+)\b",
                          re.IGNORECASE)
_PART = re.compile(r"(?m)^[ \t]*PART\s+([A-Z]+|\d+)\b", re.IGNORECASE)
_TITLE = re.compile(r"(?m)^[ \t]*TITLE\s+([A-Z]+|\d+)\b", re.IGNORECASE)
_ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7,
          "viii": 8, "ix": 9, "x": 10, "xi": 11, "xii": 12, "xiii": 13,
          "xiv": 14, "xv": 15, "xvi": 16, "xvii": 17, "xviii": 18, "xix": 19,
          "xx": 20}
_NUMBER_WORD = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}

# The dataset is flattened text. Without an explicit boundary, Article-like
# headings and decimal row labels in annexes are parsed as provisions of the
# focal act. Only uppercase line-start headings count as a boundary; this does
# not match ordinary Article titles such as "Annexes".
_ANNEX_START = re.compile(
    r"(?m)^[ \t]*(?:ANNEX(?:ES)?|APPENDIX)"
    r"(?:[ \t]+(?:[IVXLC]+|\d+[A-Z]?))?"
    r"(?:[ \t]*[:\-–—]?[ \t]+[A-Z][^\n]*|[ \t]*)$"
)
_ANNEX_ID = re.compile(r"^[ \t]*(ANNEX(?:ES)?|APPENDIX)"
                       r"(?:[ \t]+([IVXLC]+|\d+))?", re.IGNORECASE)
ANNEX_CHUNK_CHARS = 4_000
TOC_HEADING_GAP = 2_000

# "Article 5", "Article 5a", "Article 5 Subject matter"
_ART = re.compile(r"(?m)^[ \t]*Article\s+(\d+[a-z]?)\b")
# "1." / "1)" at line start = numbered paragraph within an Article
_PARA = re.compile(r"(?m)^[ \t]*(\d{1,3})[.)]\s+")
# "(a)" / "(i)" at line start = lettered/roman point within a paragraph
_POINT = re.compile(r"(?m)^[ \t]*\(([a-z]{1,3}|[ivxl]{1,5})\)\s+")
_POINT_ANY = re.compile(r"(?m)^[ \t]*\((\d{1,3}|[a-z]{1,3}|[ivxl]{1,5})\)\s+")

MIN_CHARS = 30


def _number(raw: str) -> str | None:
    """Normalise Arabic, Roman and English heading numbers."""
    low = raw.lower()
    if raw.isdigit():
        return str(int(raw))
    num = _ROMAN.get(low) or _NUMBER_WORD.get(low)
    return str(num) if num is not None else None


def _annex_chunks(text: str) -> list[str]:
    """Split an annex tail into bounded, deterministic evidence passages."""
    chunks = []
    pos = 0
    while pos < len(text):
        end = min(len(text), pos + ANNEX_CHUNK_CHARS)
        if end < len(text):
            # Prefer a line boundary, but never create a tiny chunk because a
            # flattened table happens not to contain newlines nearby.
            cut = text.rfind("\n", pos + ANNEX_CHUNK_CHARS // 2, end)
            if cut > pos:
                end = cut
        block = text[pos:end].strip()
        if block:
            chunks.append(block)
        pos = max(end, pos + 1)
    return chunks


def _annex_boundary(text: str) -> int | None:
    """Find the real annex body, skipping a compact table-of-contents list.

    EUR-Lex-Sum often contains ``ANNEX I, ANNEX II, ...`` once in a contents
    list and again where the annex text starts. A compact initial run containing
    at least three distinct annex numbers followed by a repeated ANNEX I is a
    contents list; the repeated I is the true boundary.
    """
    matches = list(_ANNEX_START.finditer(text))
    if not matches:
        return None

    def ident(m):
        x = _ANNEX_ID.match(m.group(0))
        if not x:
            return "", None
        return x.group(1).lower(), _number(x.group(2)) if x.group(2) else None

    first_kind, first_num = ident(matches[0])
    if first_kind == "annex" and first_num == "1":
        dense = [matches[0]]
        for m in matches[1:]:
            if m.start() - dense[-1].start() > TOC_HEADING_GAP:
                break
            dense.append(m)
        distinct = {ident(m)[1] for m in dense if ident(m)[1] is not None}
        if len(distinct) >= 3:
            for m in matches[1:]:
                kind, num = ident(m)
                if kind == "annex" and num == "1":
                    return m.start()
    return matches[0].start()


def segment_act(text: str, doc_id: int, doc_name: str,
                uid_version: str = "v1",
                segmentation_version: str = "legacy") -> list[Passage]:
    """Article -> paragraph -> point. Returns Passage records with numeric paths.

    `uid_version`:
      "v1" (DEFAULT, unchanged) — uid = f"{doc_id}-{idx}-{'.'.join(path)}".
            `idx` is the ARTICLE index, so every paragraph and point inside one
            Article shares it; two passages that also share a path therefore
            collide and `Corpus.by_uid` silently keeps only the last. Retained
            as the default so every v1 artefact stays reproducible.
      "v2" — uid = f"{doc_id}:v2:{ordinal:06d}:{'/'.join(path)}" where
            `ordinal` increments for every passage ACTUALLY added to this
            document. Deterministic across runs (document order is
            deterministic) and unique by construction.
    """
    if uid_version not in ("v1", "v2"):
        raise ValueError(f"uid_version must be 'v1' or 'v2', got {uid_version!r}")
    if segmentation_version not in ("legacy", "region-v2"):
        raise ValueError("segmentation_version must be 'legacy' or 'region-v2', "
                         f"got {segmentation_version!r}")
    text = clean(text)
    annex_start = None
    if segmentation_version == "region-v2":
        annex_start = _annex_boundary(text)
    main_text = text if annex_start is None else text[:annex_start]
    annex_text = "" if annex_start is None else text[annex_start:]
    arts = [(m.start(), m.group(1)) for m in _ART.finditer(main_text)]
    passages: list[Passage] = []
    ordinal = 0                       # v2 only; counts passages actually added

    def add(path: tuple[str, ...], body: str, idx: int,
            region: str = "main") -> None:
        nonlocal ordinal
        if len(body.strip()) < MIN_CHARS or not path:
            return
        if uid_version == "v2":
            uid = f"{doc_id}:v2:{ordinal:06d}:{'/'.join(path)}"
        else:
            uid = f"{doc_id}-{idx}-{'.'.join(path)}"
        ordinal += 1
        passage = Passage(uid=uid, doc_id=doc_id, doc_name=doc_name,
                          passage_id=".".join(path), path=path, text=body)
        # Passage is shared with the frozen Phase-1 pipeline. A dynamic
        # attribute keeps that schema untouched while making the EU source zone
        # available to EuResolver and the hierarchical context builder.
        passage.region = region
        passages.append(passage)

    def add_points(parent_path: tuple[str, ...], block: str, idx: int) -> None:
        """Add numeric points and their lettered children, or direct letters."""
        markers = [(m.start(), m.group(1).lower())
                   for m in _POINT_ANY.finditer(block)]
        numeric = [(s, val) for s, val in markers if val.isdigit()]
        if numeric:
            for nk, (ns, nval) in enumerate(numeric):
                ne = numeric[nk + 1][0] if nk + 1 < len(numeric) else len(block)
                nbody = block[ns:ne]
                add(parent_path + (nval,), nbody, idx)
                letters = [(m.start(), m.group(1).lower())
                           for m in _POINT.finditer(nbody)]
                for lk, (ls, letter) in enumerate(letters):
                    le = letters[lk + 1][0] if lk + 1 < len(letters) else len(nbody)
                    add(parent_path + (nval, letter), nbody[ls:le], idx)
        else:
            pts = [(m.start(), m.group(1).lower())
                   for m in _POINT.finditer(block)]
            for k, (qs, letter) in enumerate(pts):
                qe = pts[k + 1][0] if k + 1 < len(pts) else len(block)
                add(parent_path + (letter,), block[qs:qe], idx)

    # CHAPTER headings become their own passages at path ("chapter N",),
    # matching how resolve._FUSED reads "Chapter 4" -> ("chapter 4",).
    chaps = []
    if segmentation_version == "region-v2":
        structures = []
        for kind, pattern in (("part", _PART), ("title", _TITLE),
                              ("chapter", _CHAP)):
            for m in pattern.finditer(main_text):
                # Amendment provisions frequently contain prose such as
                # "Chapter III, containing Articles 15 to 29, is deleted".
                # It begins at a line boundary after flattening, but it is a
                # reference to the amended act—not a structural heading in
                # the focal act.  A comma immediately after the identifier is
                # the stable discriminator; genuine headings are standalone
                # or use a dash/colon before their title.
                line_end = main_text.find("\n", m.end())
                line_end = len(main_text) if line_end < 0 else line_end
                if main_text[m.end():line_end].lstrip().startswith(","):
                    continue
                num = _number(m.group(1))
                if num:
                    structures.append((m.start(), kind, num))
        structures.sort()
        part = title = None
        for pos, kind, num in structures:
            if kind == "part":
                part, title = num, None
            elif kind == "title":
                title = num
            else:
                path = tuple(x for x in (
                    f"part {part}" if part else None,
                    f"title {title}" if title else None,
                    f"chapter {num}") if x)
                chaps.append((pos, num, path))
    else:
        for m in _CHAP_LEGACY.finditer(main_text):
            num = _number(m.group(1))
            if num:
                chaps.append((m.start(), num, (f"chapter {num}",)))

    for i, (cs, cnum, cpath) in enumerate(chaps):
        ce = chaps[i + 1][0] if i + 1 < len(chaps) else len(main_text)
        # BODY IS THE HEADING BLOCK ONLY — deliberately NOT the chapter's full
        # span. A 4,000-char body contains the Article headings that live
        # inside the chapter, and the detector reads "Article 88" in a heading
        # as a citation: the 2026-08-10 audit found 15/100 sampled edges were
        # chapter->contained-article artefacts of exactly this kind. Those are
        # structural containment, not references, and they would distort
        # community detection by linking each chapter to everything under it.
        # Stop at the first Article heading inside the chapter.
        block = main_text[cs:ce]
        first_art = _ART.search(block)
        if first_art:
            block = block[: first_art.start()]
        add(cpath, block[:1200], 10_000 + i)

    if not arts:                      # recitals-only or unparseable: one blob
        add(("0",), main_text, 0)
        for j, block in enumerate(_annex_chunks(annex_text)):
            add(("annex-zone", f"chunk {j + 1}"), block, 20_000 + j,
                region="annex")
        return passages

    # preamble (recitals) before Article 1
    if arts[0][0] > MIN_CHARS:
        add(("0",), main_text[: arts[0][0]], 0)

    for i, (start, num) in enumerate(arts):
        end = arts[i + 1][0] if i + 1 < len(arts) else len(main_text)
        body = main_text[start:end]
        apath = canon(num)            # "5a" -> ("5a",)
        if not apath:
            continue
        add(apath, body, i)           # the Article as a whole

        # numbered paragraphs inside this Article
        paras = [(m.start(), m.group(1)) for m in _PARA.finditer(body)]
        for j, (ps, pnum) in enumerate(paras):
            pe = paras[j + 1][0] if j + 1 < len(paras) else len(body)
            pbody = body[ps:pe]
            ppath = apath + (pnum,)
            add(ppath, pbody, i)

            if segmentation_version == "region-v2":
                # EU definition lists use numeric points with lettered
                # subpoints: Article 4(1), point (15)(a). Preserve the complete
                # path instead of flattening (a) directly under paragraph 1.
                add_points(ppath, pbody, i)
            else:
                pts = [(m.start(), m.group(1)) for m in _POINT.finditer(pbody)]
                for k, (qs, letter) in enumerate(pts):
                    qe = pts[k + 1][0] if k + 1 < len(pts) else len(pbody)
                    add(ppath + (letter.lower(),), pbody[qs:qe], i)

        # Some definition Articles have numbered points but no numbered
        # paragraph (e.g. "point (10) of Article 2"). Preserve those paths too.
        if segmentation_version == "region-v2" and not paras:
            add_points(apath, body, i)

    # Annexes remain available to hierarchical summarisation, but are isolated
    # from the act's Article tree and bounded so one flattened annex cannot
    # become a hundreds-of-thousands-character passage.
    for j, block in enumerate(_annex_chunks(annex_text)):
        add(("annex-zone", f"chunk {j + 1}"), block, 20_000 + j, region="annex")
    return passages


# ---- cross-document: CELEX identifiers ------------------------------------
CITE = re.compile(r"(Regulations?|Directives?|Decisions?)\s+"
                  r"(?:\(?(?:EU|EC|EEC|Euratom)\)?\s*)?(?:No\s*)?"
                  r"(\d{1,4})/(\d{1,4})(?:/(?:EU|EC|EEC|Euratom))?",
                  re.IGNORECASE)
_T = {"Regulation": "R", "Directive": "L", "Decision": "D"}


def to_celex(kind: str, a: str, b: str) -> str:
    """EU cites as 'YYYY/NNN' (post-2015) or 'NNN/YYYY' (older)."""
    ai, bi = int(a), int(b)
    base_kind = kind.lower().rstrip("s")
    # Directives/Decisions commonly use two-digit year first (96/67/EC),
    # unlike old Regulations which normally use number/year (765/2008).
    if base_kind in {"directive", "decision"} and ai < 100:
        year, num = (1900 + ai if ai >= 50 else 2000 + ai), bi
    else:
        year, num = (ai, bi) if ai > 1950 else (bi, ai)
    if year < 100:
        year += 1900 if year > 50 else 2000
    t = {"regulation": "R", "directive": "L", "decision": "D"}[base_kind]
    return f"3{year}{t}{num:04d}"


def cited_celex(text: str) -> set[str]:
    out = set()
    for kind, a, b in CITE.findall(text):
        try:
            out.add(to_celex(kind, a, b))
        except Exception:
            pass
    return out


# ---- loader ---------------------------------------------------------------
def load_eurlexsum(splits=("train", "validation", "test"), limit: int | None = None,
                   seed: int = 41, sector: str | None = None,
                   uid_version: str = "v1", strict_unique: bool | None = None,
                   segmentation_version: str = "legacy"
                   ) -> tuple[Corpus, dict[int, str], dict[str, int]]:
    """Returns (corpus, doc_id -> celex, celex -> doc_id).

    `limit` takes a RANDOM sample, not the first N. CELEX ids sort by sector,
    so `sorted(...)[:200]` returns all 150 international agreements (sector 2)
    before any legislation (sector 3) — an unrepresentative slice that produced
    misleading segmentation and precision numbers on 2026-08-10. Sector mix of
    the English corpus: 3=1,339 legislation, 2=150 agreements, 4=15.

    `sector` optionally restricts to one CELEX sector ("3" = legislation).

    `uid_version` — see segment_act. Defaults to "v1" so existing artefacts
    reproduce exactly. v2 scripts must pass uid_version="v2".

    `strict_unique` — assert len(passages) == len(by_uid). Defaults to True for
    v2 (where uniqueness is guaranteed by construction, so a failure is a bug)
    and False for v1 (where collisions are a known, documented property).
    The v1 collision count is always reported on the returned corpus as
    `corpus.n_uid_collisions` for diagnostics.
    """
    import random
    from huggingface_hub import hf_hub_download
    if strict_unique is None:
        strict_unique = (uid_version == "v2")
    recs = {}
    for split in splits:
        p = hf_hub_download("dennlinger/eur-lex-sum",
                            f"data/english/{split}.json", repo_type="dataset")
        for line in open(p):
            if line.strip():
                r = json.loads(line)
                recs[r["celex_id"]] = r
    celexes = sorted(recs)
    if sector:
        celexes = [c for c in celexes if c.startswith(sector)]
    if limit and limit < len(celexes):
        celexes = sorted(random.Random(seed).sample(celexes, limit))
    corpus = Corpus()
    id2celex, celex2id = {}, {}
    for doc_id, cx in enumerate(celexes):
        id2celex[doc_id] = cx
        celex2id[cx] = doc_id
        for p in segment_act(recs[cx]["reference"], doc_id, cx,
                             uid_version=uid_version,
                             segmentation_version=segmentation_version):
            corpus.add(p)
    n_collisions = len(corpus.passages) - len(corpus.by_uid)
    corpus.n_uid_collisions = n_collisions          # attribute, not a schema change
    if strict_unique and n_collisions:
        raise AssertionError(
            f"uid_version={uid_version!r} produced {n_collisions} UID collisions "
            f"({len(corpus.passages)} passages, {len(corpus.by_uid)} unique) — "
            "this must never happen for v2")
    return corpus, id2celex, celex2id
