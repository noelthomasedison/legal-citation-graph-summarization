"""EU-aware resolver: restores the "refuse to guess" guard for EUR-Lex.

WHY THIS EXISTS. Phase 1's `Resolver._target_doc` refuses to resolve a mention
that names a document outside the corpus ("of the PRMS Guidelines") — the
guard that keeps precision high. But it short-circuits when `use_aliases=False`:

    if not self.use_aliases:
        return source_doc, "default"

The Phase 3 EU run set `use_aliases=False` (EU acts cite by CELEX, not by
informal alias) and thereby switched the guard off too. The audit
(reports/eurlex_audit_sample.md) showed the damage: ~37% of sampled edges had
context naming an EXTERNAL instrument — Vietnamese "Land Law 2013",
"Decree No. 02/ND-CP", "Appendix 14-A", "of this Annex" — force-resolved into
the focal act's own Article numbering. All hand-checked examples were wrong.

`phase1/src/regkg/resolve.py` is NOT modified: Phase 1's ablation rung 3 and
the CUAD graph were both produced with `use_aliases=False`, so changing that
branch would silently alter already-reported results. The EU behaviour is
added here by subclassing instead.

WHY THE PHASE-1 GUARD WOULD NOT HAVE CAUGHT THESE ANYWAY. It requires the
pattern "<mention> of/under/in [the] Xxx". EU citations often omit the
preposition entirely — "Article 100 Land Law 2013" — so a new EU-specific
pattern is genuinely needed, not merely the old one re-enabled.
"""
from __future__ import annotations

import re

from regkg.evaluate import PredEdge
from regkg.resolve import Resolver, parse_core


class EuResolver(Resolver):
    """Resolver that refuses mentions pointing outside the focal act."""

    # Instrument words that mark a THIRD-PARTY legal text. "Article 100 Land
    # Law 2013" / "Articles 5, 13 and 14, Decree No. 02/ND-CP".
    _EXT_INSTRUMENT = re.compile(
        r"^\s*[-–,]?\s*(?:of\s+|under\s+|in\s+|to\s+)?(?:the\s+)?"
        r"(Law|Decree|Ordinance|Code|Act\b|Treaty|Convention|Protocol|"
        r"Agreement|Charter|Statute|Rules?\s+of\s+Procedure|TFEU|TEU)",
        re.IGNORECASE)

    # The reference lives in an Annex/Appendix/Schedule, which we do not
    # segment: "Article 8(4) of Section 2 of Part B of this Annex".
    #
    # NB the obvious phrasing — r"^(?:\s*\S+){0,8}?\s+of\s+(?:this\s+)?(Annex|...)"
    # — is a trap: the nested quantifier backtracks catastrophically on the
    # COMMON case (tails that do not match), measured at 1,196 us/call vs
    # 0.9 us for the search below. That is ~1,340x slower and cost ~8 minutes
    # of pure waste across 455,810 mentions on 2026-08-10. A plain search over
    # a bounded window does the same job; the window cap is what keeps it
    # local to the mention.
    _IN_ANNEX = re.compile(
        r"\bof\s+(?:this\s+)?(Annex|Appendix|Schedule)\b", re.IGNORECASE)
    _ANNEX_WINDOW = 60          # chars after the mention to consider "local"

    # Another EU instrument by name. Resolvable only if we hold that act.
    _EU_INSTRUMENT = re.compile(
        r"\s*(?:of\s+|under\s+|in\s+)?(?:the\s+)?"
        r"(?:(?:Council|Commission)\s+)?"
        r"(Regulations?|Directives?|Decisions?)"
        r"(?:\s+\(?(?:EU(?:,\s*Euratom)?|EC|EEC|Euratom)\)?)?"
        r"\s+(?:No\s*)?(\d{1,4})/(\d{1,4})"
        r"(?:/(?:EU|EC|EEC|Euratom))?",
        re.IGNORECASE)
    _THIS_INSTRUMENT = re.compile(
        r"^\s*(?:of|under|in)\s+this\s+"
        r"(?:Regulation|Directive|Decision|Agreement)\b",
        re.IGNORECASE)
    _THAT_INSTRUMENT = re.compile(
        r"^\s*(?:of|under|in)\s+that\s+(?:Regulation|Directive|Decision)\b",
        re.IGNORECASE)

    # A modifying act often places the owner only in the parent Article title:
    #
    #   Article 28 — Amendments to Directive 2001/83/EC
    #   3. in Article 4, the following paragraph shall be added: ...
    #
    # Child passages contain no instrument name, so an unqualified Article 4
    # must inherit the amended instrument rather than fall back to the focal
    # Regulation's own Article 4. Only a single explicit instrument is safe.
    _AMENDMENT_HEADING = re.compile(
        r"^(?:Amendments?\s+to|Amendment\s+of)\s+"
        r"(?:(?:Council|Commission)\s+)?"
        r"(Regulation|Directive|Decision)"
        r"(?:\s+\(?(?:EU(?:,\s*Euratom)?|EC|EEC|Euratom)\)?)?"
        r"\s+(?:No\s*)?(\d{1,4})/(\d{1,4})"
        r"(?:/(?:EU|EC|EEC|Euratom))?\s*$",
        re.IGNORECASE | re.MULTILINE)

    # A named instrument can scope a whole sentence/list and appear before the
    # sampled mention (Charter examples) or after the last list item
    # ("Articles 11(1), 13(1), 13(2) ... of Regulation 1031/2010").
    _SCOPED_EXTERNAL = re.compile(
        r"\b(Charter|TFEU|TEU|Treaty|Convention|Protocol|Law|Decree|"
        r"Ordinance|Code|Statute|Rules?\s+of\s+Procedure)\b", re.IGNORECASE)

    # Mentions whose own keyword names a structure we do not segment.
    _UNMODELLED_KEYWORD = re.compile(
        r"^(annex|appendix|schedule|section|sections|rule|rules|guidance)$",
        re.IGNORECASE)

    # RELATIVE references. In EU acts "the measures referred to in paragraph 1"
    # inside Article 29 means Article 29(1) — NOT Article 1. ADGM never needed
    # this because "Rule 6.1" is always absolute, so the inherited grammar
    # resolves these to the top-level Article and is wrong: the 2026-08-10
    # audit found 10/100 sampled edges were relative refs landing on a
    # top-level Article. Such a mention is resolved RELATIVE to the source
    # passage's own Article unless it explicitly names another Article.
    _RELATIVE_KEYWORD = re.compile(r"^(paragraph|paragraphs|point|points|"
                                   r"subparagraph|subparagraphs)$", re.IGNORECASE)
    _ARTICLE_CUE = re.compile(
        r"^\s*(?:\([^)]{0,30}\)\s*)?(?:of|in|to|under)\s+"
        r"(?:(?P<which>that|this|the)\s+)?Article"
        r"(?:\s+(?P<core>\d+[a-z]?(?:\([^)]{1,3}\))*))?\b",
        re.IGNORECASE)
    _PRECEDING_ARTICLE = re.compile(
        r"\bArticle\s+(\d+[a-z]?)(?:\([^)]{1,3}\))*", re.IGNORECASE)
    _NESTED_POINT_PREFIX = re.compile(
        r"\bpoints?\s*(?:\((?P<paren>\d+[a-z]?)\)|"
        r"(?P<bare>\d+[a-z]?))(?:\((?P<sub>[a-z0-9]{1,3})\))?"
        r"(?:\s+of)?\s*$", re.IGNORECASE)
    _QUALIFIED_CHAPTER = re.compile(
        r"Part\s+([A-Z]+|\d+)\s*,?\s*Title\s+([A-Z]+|\d+)\s*,?\s*$",
        re.IGNORECASE)
    _STRUCT_NUM = {
        "i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5",
        "vi": "6", "vii": "7", "viii": "8", "ix": "9", "x": "10",
        "one": "1", "two": "2", "three": "3", "four": "4",
        "five": "5", "six": "6", "seven": "7", "eight": "8",
        "nine": "9", "ten": "10",
    }

    def __init__(self, *a, celex2id: dict[str, int] | None = None,
                 progress_every: int = 20_000, **kw):
        super().__init__(*a, **kw)
        self.celex2id = celex2id or {}
        self.n_refused_external = 0
        self.n_refused_annex = 0
        self.n_routed_celex = 0
        self.n_relative = 0
        self.n_refused_annex_number = 0
        self.n_refused_duplicate_path = 0
        self.n_refused_qualified = 0
        self.n_nested_point = 0
        self.n_refused_date = 0
        self.n_refused_heading = 0
        self.n_routed_amendment = 0
        self.n_refused_amendment = 0
        self.progress_every = progress_every
        self._active_passage = None
        self._amendment_owner: dict[tuple[int, str], int | None] = {}
        self._index_amendment_owners()

    def _index_amendment_owners(self) -> None:
        """Index unambiguous amended-instrument ownership by parent Article."""
        from eurlex_ingest import to_celex

        for p in self.corpus.passages:
            if len(p.path) != 1 or getattr(p, "region", "main") != "main":
                continue
            matches = list(self._AMENDMENT_HEADING.finditer(p.text[:500]))
            if len(matches) != 1:
                continue
            match = matches[0]
            celex = to_celex(match.group(1), match.group(2), match.group(3))
            # None is meaningful: an explicit amended act that is absent from
            # the corpus must cause refusal rather than local fallback.
            self._amendment_owner[(p.doc_id, p.path[0])] = self.celex2id.get(celex)

    def _active_amendment_owner(self, source_doc: int) -> tuple[bool, int | None]:
        p = self._active_passage
        if p is None or p.doc_id != source_doc or not p.path:
            return False, None
        key = (source_doc, p.path[0])
        return key in self._amendment_owner, self._amendment_owner.get(key)

    # ------------------------------------------------------------------
    @staticmethod
    def _sentence_bounds(text: str, start: int, end: int) -> tuple[int, int]:
        """Return a bounded local sentence/clause for instrument propagation."""
        left = max(text.rfind(ch, max(0, start - 500), start)
                   for ch in (".", "!", "?", "\n"))
        left = max(left + 1, start - 500, 0)
        rights = [text.find(ch, end, min(len(text), end + 500))
                  for ch in (".", "!", "?", "\n", ";")]
        rights = [x for x in rights if x >= 0]
        right = min(rights) if rights else min(len(text), end + 500)
        return left, right

    @classmethod
    def _struct_num(cls, raw: str) -> str | None:
        return str(int(raw)) if raw.isdigit() else cls._STRUCT_NUM.get(raw.lower())

    def _relative_article(self, p, text: str, m, cue) -> tuple[str, ...] | None:
        """Resolve the Article anchor for paragraph(s) of this/that/Article N."""
        explicit = cue.group("core") if cue else None
        which = (cue.group("which") or "").lower() if cue else ""
        if explicit:
            parsed = parse_core(explicit)
            return parsed[:1] if parsed else None
        if not cue or which == "this":
            return p.path[:1] if p.path else None
        # "that/the Article" is anaphoric: use the latest explicit Article in
        # the same bounded sentence before the relative mention.
        lo, _ = self._sentence_bounds(text, m.start, m.end)
        prior = list(self._PRECEDING_ARTICLE.finditer(text[lo:m.start]))
        return (prior[-1].group(1).lower(),) if prior else None

    def _resolve_mention(self, p, text, m):
        """Resolve relative references against the SOURCE passage's Article.

        "paragraph 1" inside Article 29(2) means 29(1). We rewrite the lookup
        by prefixing the source's own Article component, then defer to the
        inherited machinery so guards, ranges and attribution still apply.
        """
        self._active_passage = p
        kw = (m.keyword or "").strip()

        if not kw and re.fullmatch(r"\d{1,2}\.\d{1,2}\.\d{4}", m.core):
            self.n_refused_date += 1
            return []

        # Uppercase line-start PART/CHAPTER/TITLE labels are structural
        # boundaries copied into an Article/annex passage, not citations.
        if (kw and kw.isupper() and kw.lower().rstrip("s")
                in {"part", "chapter", "title", "section"}
                and (m.start == 0 or text[m.start - 1] == "\n")):
            self.n_refused_heading += 1
            return []

        # Segment headings are structural labels, not citations. This also
        # blocks incorporated/correlation-table headings such as "Article 5\n"
        # from linking to the focal act's unrelated Article 5.
        if (kw.lower().rstrip("s") == "article"
                and re.fullmatch(r"\d+[a-z]?(?:\.\d+[a-z]?)*(?:\([^)]{1,3}\))*",
                                 m.core,
                                 re.IGNORECASE)):
            line_start = m.start == 0 or text[m.start - 1] == "\n"
            heading_tail = text[m.end:m.end + 160]
            heading_shape = (re.match(r"[ \t]*\n", heading_tail)
                             or re.match(r"[ \t]*:[^\n]{0,120}(?:\n|$)",
                                         heading_tail))
            if line_start and heading_shape:
                return []

        if (kw.lower().rstrip("s") == "chapter" and m.start == 0 and p.path
                and p.path[-1] == f"chapter {self._struct_num(m.core)}"):
            self.n_refused_heading += 1
            return []

        # Bare decimals in an annex/table/form are row identifiers, not legal
        # references. Explicit Article/Chapter/etc. mentions remain eligible.
        if getattr(p, "region", "main") == "annex" and not kw:
            self.n_refused_annex_number += 1
            return []

        # Annex tariff schedules use "Chapters 25 to 97" for Harmonised
        # System commodity chapters. They are not chapters of the focal act.
        if (getattr(p, "region", "main") == "annex" and kw.lower().rstrip("s")
                == "chapter"):
            self.n_refused_annex += 1
            return []

        # In an annex, an unqualified Article normally belongs to an
        # incorporated protocol/correlation table, not to the enclosing act.
        # Keep only explicitly scoped cross-act or "this Regulation" forms.
        if (getattr(p, "region", "main") == "annex"
                and kw.lower().rstrip("s") == "article"):
            tail80 = text[m.end:m.end + 180]
            explicit = self._EU_INSTRUMENT.match(tail80)
            if not explicit and kw.lower().endswith("s"):
                _, hi = self._sentence_bounds(text, m.start, m.end)
                explicit = self._EU_INSTRUMENT.search(text[m.end:hi])
            focal = self._THIS_INSTRUMENT.match(tail80)
            if not explicit and not self._THAT_INSTRUMENT.match(tail80) and not focal:
                self.n_refused_annex += 1
                return []

        # Complete a detector's partial inverted match:
        # "point (15)(a) of Article 4(1)" used to surface only as
        # "(a) of Article 4(1)" and resolve to the unrelated 4/1/a.
        prefix = text[max(0, m.start - 50):m.start]
        nested = self._NESTED_POINT_PREFIX.search(prefix)
        parsed = parse_core(m.core)
        if nested and kw.lower().rstrip("s") == "article" and parsed:
            doc, kind = self._target_doc(text, m, p.doc_id)
            if kind == "unknown":
                return []
            point = (nested.group("paren") or nested.group("bare")).lower()
            sub = (nested.group("sub") or "").lower()
            if m.text.lstrip().startswith("("):
                comps = parsed[:-1] + (point, parsed[-1])
            else:
                comps = parsed + (point,) + ((sub,) if sub else ())
            tgt, how = self._try(doc, comps)  # never ascend an incomplete chain
            if tgt is None or tgt.uid == p.uid:
                return []
            self.n_nested_point += 1
            return [PredEdge(p.uid, tgt.uid,
                             mention=text[nested.start() + max(0, m.start - 50):m.end],
                             how=how + "+nested-point", keyword=m.keyword or "")]

        # Fully qualified Chapter references must use their Part/Title path;
        # selecting the first generic Chapter 2 is a silent wrong answer.
        if kw.lower().rstrip("s") == "chapter":
            q = self._QUALIFIED_CHAPTER.search(text[max(0, m.start - 100):m.start])
            if q:
                part, title = self._struct_num(q.group(1)), self._struct_num(q.group(2))
                chapter = self._struct_num(m.core)
                doc, kind = self._target_doc(text, m, p.doc_id)
                if kind != "unknown" and part and title and chapter:
                    tgt, how = self._try(
                        doc, (f"part {part}", f"title {title}", f"chapter {chapter}"))
                    if tgt is not None and tgt.uid != p.uid:
                        return [PredEdge(p.uid, tgt.uid, mention=m.text,
                                         how=how + "+qualified", keyword=m.keyword or "")]
                self.n_refused_qualified += 1
                return []

            # Unqualified structural references may use only a unique fused
            # Chapter path. Never fall back from "Chapter 4" to Article 4.
            doc, kind = self._target_doc(text, m, p.doc_id)
            chapter = self._struct_num(m.core)
            if kind != "unknown" and chapter and not m.range_end:
                cands = self.suffix.lookup(doc, (f"chapter {chapter}",))
                if len(cands) == 1 and cands[0].uid != p.uid:
                    return [PredEdge(p.uid, cands[0].uid, mention=m.text,
                                     how="suffix-structural", keyword=m.keyword or "")]
            self.n_refused_qualified += 1
            return []

        if kw and self._RELATIVE_KEYWORD.match(kw) and p.path:
            core = m.core.strip()
            parsed_core = parse_core(core)
            if (parsed_core and
                    re.fullmatch(r"\d+[a-z]?", parsed_core[0], re.IGNORECASE)):
                cue = self._ARTICLE_CUE.match(text[m.end:m.end + 80])
                article = self._relative_article(p, text, m, cue)
                if article:
                    cores = [m.core] + (self._expand_range(m.core, m.range_end)
                                        if m.range_end else [])
                    out = []
                    for item in cores:
                        components = parse_core(item)
                        if not components:
                            continue
                        tgt_path = article + components
                        hit = self.corpus.by_path.get((p.doc_id, tgt_path))
                        if hit and hit[0].uid != p.uid:
                            out.append(PredEdge(p.uid, hit[0].uid, mention=m.text,
                                                how="relative", keyword=m.keyword or ""))
                    if out:
                        self.n_relative += len(out)
                    return out                 # relative target absent: refuse

        out = super()._resolve_mention(p, text, m)
        kept = []
        for edge in out:
            tgt = self.corpus.by_uid.get(edge.target_uid)
            if (tgt is not None and tgt.doc_id == p.doc_id and tgt.path == p.path
                    and tgt.uid != p.uid):
                self.n_refused_duplicate_path += 1
                continue
            kept.append(edge)
        return kept

    def run(self, passages):
        """Same as Resolver.run, but prints progress.

        The base implementation is silent, so a 2h15m run on 2026-08-10 gave no
        way to distinguish "working" from "hung".

        CRITICAL: batches must contain WHOLE DOCUMENTS. Resolver.run does
        deepest-container attribution by comparing each passage against its
        descendants within the same doc_id; splitting a document across batches
        would hide descendants from their parent and wrongly keep duplicate
        edges. Because attribution is within-document only, batching by whole
        documents is exactly equivalent to one big call.
        """
        import time
        by_doc: dict[int, list] = {}
        for p in passages:
            by_doc.setdefault(p.doc_id, []).append(p)

        out, t0 = [], time.time()
        done_p, n = 0, len(passages)
        batch: list = []
        for d in sorted(by_doc):
            batch.extend(by_doc[d])
            if len(batch) >= self.progress_every:
                out.extend(super().run(batch))
                done_p += len(batch)
                batch = []
                el = time.time() - t0
                eta = el / max(done_p, 1) * (n - done_p)
                print(f"  resolve {done_p:,}/{n:,} passages | {len(out):,} edges "
                      f"| {el/60:.1f} min elapsed, ~{eta/60:.1f} min left",
                      flush=True)
        if batch:
            out.extend(super().run(batch))
        print(f"  resolve complete: {len(out):,} edges in "
              f"{(time.time()-t0)/60:.1f} min", flush=True)
        return out

    def _target_doc(self, text: str, m, source_doc: int) -> tuple[int, str]:
        tail = text[m.end:m.end + 220]
        head = text[max(0, m.start - 80):m.start]
        lo, hi = self._sentence_bounds(text, m.start, m.end)
        scope = text[lo:hi]

        # 1. the mention itself names an unmodelled structure ("Appendix 14")
        if m.keyword and self._UNMODELLED_KEYWORD.match(m.keyword.strip()):
            self.n_refused_annex += 1
            return source_doc, "unknown"

        # "Annex X, Part 4": the Annex owner precedes the detected Part.
        if re.search(r"\b(?:Annex|Appendix|Schedule)\s+[A-Z0-9IVXLC-]+\b"
                     r"[^.;\n]{0,50}$",
                     head, re.IGNORECASE):
            self.n_refused_annex += 1
            return source_doc, "unknown"

        # The target sits inside an Annex/Appendix, even if a later part of the
        # sentence names an EU act. Annex ownership outranks act routing.
        if self._IN_ANNEX.search(tail[: self._ANNEX_WINDOW]):
            self.n_refused_annex += 1
            return source_doc, "unknown"

        # An explicit focal-act owner outranks every later instrument in the
        # sentence.  Without this guard, a plural/list citation such as
        # "Articles 4 and 5 of this Regulation ... Article 45 of Directive
        # 2015/2366" is incorrectly propagated to the later Directive.
        in_amendment, amendment_owner = self._active_amendment_owner(source_doc)
        if self._THIS_INSTRUMENT.match(tail):
            if in_amendment:
                if amendment_owner is None:
                    self.n_refused_amendment += 1
                    return source_doc, "unknown"
                self.n_routed_amendment += 1
                return amendment_owner, "amended-instrument"
            return source_doc, "default"

        # 2. another EU act by name. A singular Article uses only an immediate
        # "of Regulation ..." anchor. A plural/list mention may propagate the
        # instrument from the end of that list. "of that Regulation" inherits
        # the most recently named EU act in the preceding local paragraph.
        direct = self._EU_INSTRUMENT.match(tail)
        plural_or_list = bool(m.keyword and m.keyword.lower().endswith("s"))
        forward = (self._EU_INSTRUMENT.search(text[m.end:hi])
                   if plural_or_list and direct is None else None)
        before = []
        if direct is None and forward is None and self._THAT_INSTRUMENT.match(tail):
            before = list(self._EU_INSTRUMENT.finditer(
                text[max(0, m.start - 500):m.start]))
        if (direct is None and forward is None and not before and plural_or_list
                and re.search(r"Applicable\s+provisions\s*:\s*$",
                              text[max(0, m.start - 80):m.start], re.IGNORECASE)):
            before = list(self._EU_INSTRUMENT.finditer(
                text[max(0, m.start - 300):m.start]))
        eu = direct or forward or (before[-1] if before else None)
        if eu:
            kind, a, b = eu.group(1), eu.group(2), eu.group(3)
            from eurlex_ingest import to_celex
            celex = to_celex(kind.rstrip("s"), a, b)
            if celex in self.celex2id and self.celex2id[celex] != source_doc:
                self.n_routed_celex += 1
                return self.celex2id[celex], "explicit"
            return source_doc, "unknown"          # cited act not in corpus

        # 3. third-country / non-EU instrument ("Land Law 2013", "Decree No. 02")
        if self._EXT_INSTRUMENT.match(tail):
            self.n_refused_external += 1
            return source_doc, "unknown"

        # Named Charter/Treaty/etc. scope can precede all Article mentions in
        # the sentence. Never fall back to the focal act in that case.
        wider_scope = text[max(0, m.start - 500):hi]
        if self._SCOPED_EXTERNAL.search(wider_scope):
            self.n_refused_external += 1
            return source_doc, "unknown"

        # Unqualified references inside an amendment item belong to the one
        # instrument named by the parent Article heading. Explicit routing and
        # all annex/external guards above retain precedence.
        if in_amendment:
            if amendment_owner is None:
                self.n_refused_amendment += 1
                return source_doc, "unknown"
            self.n_routed_amendment += 1
            return amendment_owner, "amended-instrument"

        return super()._target_doc(text, m, source_doc)
