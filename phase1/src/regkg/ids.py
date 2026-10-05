"""Passage-ID normalisation.

The corpus has 202 distinct PassageID shapes. Everything downstream (gold
matching, hierarchy, nested expansion) depends on mapping them into one
canonical form: a tuple of lowercase components.

Observed formats (from data/raw, see reports/audit.md):
    1.1.1                       -> ("1", "1", "1")
    1.1.1.(2)                   -> ("1", "1", "1", "2")
    2.4.2.(a)                   -> ("2", "4", "2", "a")
    Part 3.Chapter 1.7.(1)      -> ("part 3", "chapter 1", "7", "1")
    Schedule 1.Part 2.Chapter 1.5.(2)
                                -> ("schedule 1", "part 2", "chapter 1", "5", "2")
    APP2.A2.1.1                 -> ("app2", "a2", "1", "1")
    1.2.1.Guidance.3.           -> ("1", "2", "1", "guidance", "3")
    SECTION I.A.1.              -> ("section i", "a", "1")
    Part 1.1.                   -> ("part 1", "1")
    1)                          -> fragment: ("1",) with is_fragment=True

Fragments (bare "N)" items, 941 in corpus) carry no positional information on
their own; ingest.py resolves their full path from document order.
"""
from __future__ import annotations

import re

_FRAGMENT_RE = re.compile(r"^\s*\(?([0-9]+|[a-z]|[ivxlc]+)\)\s*$", re.IGNORECASE)
_WS_RE = re.compile(r"\s+")


def is_fragment(passage_id: str) -> bool:
    """Bare list-item IDs like "1)" or "(a)" that need document-order context."""
    return bool(_FRAGMENT_RE.match(passage_id or ""))


def _norm_component(comp: str) -> str:
    comp = comp.strip()
    # "(1)" / "(a)" -> "1" / "a"; also strip a stray trailing ")" as in "1)"
    if comp.startswith("(") and comp.endswith(")"):
        comp = comp[1:-1]
    comp = comp.rstrip(")")
    comp = _WS_RE.sub(" ", comp)
    return comp.lower()


def canon(passage_id: str) -> tuple[str, ...]:
    """Canonicalise a PassageID into a tuple of components.

    Splitting on "." is safe because multi-word labels use spaces, not dots
    ("Part 3.Chapter 1" splits into "Part 3" / "Chapter 1"). Empty components
    from trailing dots are dropped.
    """
    if passage_id is None:
        return ()
    parts = [p for p in str(passage_id).split(".")]
    comps = tuple(c for c in (_norm_component(p) for p in parts) if c)
    return comps


def is_ancestor(ancestor: tuple[str, ...], descendant: tuple[str, ...]) -> bool:
    """True iff `ancestor` is a proper prefix of `descendant`."""
    return len(ancestor) < len(descendant) and descendant[: len(ancestor)] == ancestor


def is_same_or_descendant(target: tuple[str, ...], candidate: tuple[str, ...]) -> bool:
    """Nested-expansion test: candidate == target or lies under it."""
    return candidate == target or is_ancestor(target, candidate)
