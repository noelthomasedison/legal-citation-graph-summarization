"""Text normalisation shared by detection and resolution."""
import re

# LRM/RLM, zero-width chars, BOM — present in the corpus ("Rule ‎1.7.1")
# and they break keyword capture if left in place.
_FORMAT_CHARS = re.compile(r"[​‌‍‎‏﻿]")


def clean(text: str) -> str:
    """Strip Unicode format characters; keep length-changing edits out of
    the picture by replacing with nothing only (offsets shift together for
    detection and alias-window scanning, which both use the cleaned text)."""
    return _FORMAT_CHARS.sub("", text or "")
