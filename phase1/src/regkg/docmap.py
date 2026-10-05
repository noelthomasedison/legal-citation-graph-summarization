"""Parse DocumentMap.rtf into an alias table for cross-document resolution."""
from __future__ import annotations

import re
from pathlib import Path


def load_aliases(rtf_path: Path) -> dict[str, int]:
    """alias (lowercased) -> DocumentID. Includes acronyms and full titles."""
    raw = rtf_path.read_text(errors="ignore")
    txt = re.sub(r"\\[a-z*]+-?\d* ?", "", raw)
    txt = txt.replace("{", "").replace("}", "").replace("\\", "")
    aliases: dict[str, int] = {}
    for m in re.finditer(r"(\d+):\s*\[(.*?)\]", txt, re.DOTALL):
        doc_id = int(m.group(1))
        for name in re.findall(r'"([^"]+)"', m.group(2)):
            name = name.strip().lower()
            if name:
                aliases[name] = doc_id
            # "Fund Rules (FUNDS)" also yields the bare acronym
            par = re.search(r"\(([A-Za-z]{2,8})\)\s*$", name)
            if par:
                aliases[par.group(1).lower()] = doc_id
    return aliases


def alias_pattern(aliases: dict[str, int]) -> re.Pattern:
    """One regex matching any alias, longest-first, on word boundaries."""
    names = sorted(aliases, key=len, reverse=True)
    joined = "|".join(re.escape(n) for n in names)
    return re.compile(rf"\b({joined})\b", re.IGNORECASE)
