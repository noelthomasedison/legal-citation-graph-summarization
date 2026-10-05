"""Rule-based reference-mention detection.

Grammar mined from DEV gold ReferenceText shapes (reports: step 2 mining):
  6.6.1 | 2.2 | 3 | 61(1) | 3.1.4(2) | 10.3.2(1)(b) | 3.6A.6 | A4.3.2 | Part 4
  ranges:  6.2.7 to 6.2.16 | A4.6.14 to A4.6.21 | 47-54
  lists:   Rules 2.2.1, 2.2.2 and 2.2.3

A mention = optional keyword + core token(s); bare integers require a keyword
(precision guard — "3" alone matches prose numbers).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# core reference token: 61(1), 6.6.1, 3.6A.6, 3.1.4(2)(b), 2.1 (c), A4.3.2, APP2
# parenthetical subsection markers are short — (1) (a) (iv) — while annotation
# parens are words ("Part 4 (Authorisation)") and must NOT be swallowed
CORE = r"(?:A(?:PP)?\s?\d+\.)?\d+[A-Z]?(?:\.\d+[A-Z]?)*(?:\s?\([a-zA-Z0-9]{1,3}\))*"
KEYWORD = (r"(?:Rule|Rules|Section|Sections|Chapter|Chapters|Part|Parts|"
           r"Paragraph|Paragraphs|Article|Articles|Schedule|Schedules|"
           r"App(?:endix)?|Guidance)")

_MENTION = re.compile(
    rf"(?P<kw>{KEYWORD})?\s*"
    rf"(?P<core>{CORE})"
    rf"(?:\s*(?:to|–|—|-)\s*(?P<rng>{CORE}))?",
    re.IGNORECASE)

# "Rules 2.2.1, 2.2.2 and 2.2.3" — items after the first, sharing the keyword
_CONTINUATION = re.compile(
    rf"\s*(?:,|;|and|or|,\s*and|,\s*or)\s+"
    rf"(?P<core>{CORE})"
    rf"(?:\s*(?:to|–|—|-)\s*(?P<rng>{CORE}))?",
    re.IGNORECASE)

# inverted form: "(4) of Rule 10.3.2" / "paragraph (c) of Section 2.1"
_INVERTED = re.compile(
    rf"\((?P<sub>[a-zA-Z0-9]+)\)\s+of\s+(?P<kw>{KEYWORD})\s+(?P<core>{CORE})",
    re.IGNORECASE)

_HAS_DOT = re.compile(r"\d\.\d")


@dataclass(frozen=True)
class Mention:
    text: str            # surface form
    core: str            # first core token
    range_end: str | None
    keyword: str | None
    start: int           # char offset in passage
    end: int


def _is_prose_number(text: str, end: int) -> bool:
    """Plain decimals like '1.5 million' / '≤ 3.6 years' are not references."""
    tail = text[end: end + 12].lower()
    return bool(re.match(
        r"^\s*(?:%|per\s?cent|million|billion|times|:1"
        r"|years?\b|months?\b|days?\b|weeks?\b|y\b)", tail))


def _is_item_label(text: str, end: int) -> bool:
    """Appendix/table item numbering ('9.1<tab>Mining and Petroleum...') —
    a keyword-less number followed by tab(s)/column spacing labels a row,
    it does not cite one."""
    return bool(re.match(r"(?:\t+| {2,})", text[end: end + 4]))


def detect(text: str, alias_re: re.Pattern | None = None,
           guards: bool = True) -> list[Mention]:
    """Callers should pass textutil.clean()ed text.

    `alias_re`: optional document-alias pattern; an alias immediately before a
    bare number acts as its keyword ("... in FEES 8.").
    `guards`: enable the semantic precision guards (prose numbers, table item
    labels, comparison operators). Structural requirements (bare integers need
    a keyword/alias) are part of the grammar and stay on. Ablation rung 2.
    """
    out = []
    pos = 0
    text = text or ""
    for m in _INVERTED.finditer(text):
        out.append(Mention(text=m.group(0).strip(),
                           core=f"{m.group('core')}({m.group('sub')})",
                           range_end=None, keyword=m.group("kw"),
                           start=m.start(), end=m.end()))

    def alias_precedes(start: int) -> bool:
        if alias_re is None:
            return False
        head = text[max(0, start - 24): start]
        a = None
        for a in alias_re.finditer(head):
            pass                                   # keep last alias in head
        return a is not None and head[a.end():].strip() == ""
    while True:
        m = _MENTION.search(text, pos)
        if m is None:
            break
        pos = m.end()
        core, kw = m.group("core"), m.group("kw")
        # precision guards --------------------------------------------------
        if kw is None and alias_precedes(m.start()):
            kw = "@alias"                   # doc alias anchors the number
        if not _HAS_DOT.search(core) and "(" not in core and not kw:
            continue                        # bare integer without keyword/alias
        if kw is None and len(core) <= 3 and "." not in core:
            continue
        if guards and _is_prose_number(text, m.end()):
            continue
        if guards and kw is None and _is_item_label(text, m.end()):
            continue                        # table/appendix item numbering
        if guards and kw is None and re.search(
                r"[≤≥<>]\s*$", text[max(0, m.start() - 3): m.start()]):
            continue                        # numeric comparison ("> 3.6 and ≤ 4.3")
        out.append(Mention(text=m.group(0).strip(), core=core,
                           range_end=m.group("rng"), keyword=kw,
                           start=m.start(), end=m.end()))
        # keyworded mention: consume list continuations ("..., 2.2.2 and 2.2.3")
        if kw:
            while True:
                c = _CONTINUATION.match(text, pos)
                if c is None or (guards and _is_prose_number(text, c.end())):
                    break
                out.append(Mention(text=c.group(0).strip(), core=c.group("core"),
                                   range_end=c.group("rng"), keyword=kw,
                                   start=c.start(), end=c.end()))
                pos = c.end()
    return out
