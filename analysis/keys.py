"""Canonical text keys shared by the cleaner and the analysis code.

Standard library only, so ``clean_listens.py`` can import it without pandas.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Optional

_WHITESPACE = re.compile(r"\s+")

# Credit strings that name no real artist. They are excluded from artist
# metrics (rows stay in the cleaned data). Compared after normalize_key().
NON_ARTIST_KEYS = frozenset({
    "various artists",
    "various",
    "unknown",
    "unknown artist",
    "[unknown]",
    "<unknown>",
    "n/a",
})


def clean_text(value: Any) -> Optional[str]:
    """Display text: trim and collapse whitespace, keep case. Blank becomes None."""
    if value is None:
        return None
    normalized = _WHITESPACE.sub(" ", str(value)).strip()
    return normalized or None


def normalize_key(value: Any) -> Optional[str]:
    """Grouping key: clean_text, then Unicode NFKC, then casefold.

    NFKC folds full-width and compatibility characters (for example
    full-width Latin letters) so visually identical credits group together.
    """
    text = clean_text(value)
    if text is None:
        return None
    key = clean_text(unicodedata.normalize("NFKC", text).casefold())
    return key or None
