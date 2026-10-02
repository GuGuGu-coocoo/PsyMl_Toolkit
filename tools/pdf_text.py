"""Font-safe mathematical labels for the offline Chinese PDF renderer."""

import html
import re


def supported_glyphs(text: str) -> str:
    for old, new in {"📖": "", "ȳ": "y_mean", "ŷ": "y_hat", "−": "-", "ᵀ": "<super>T</super>",
                     "ᵢ": "<sub>i</sub>", "ⱼ": "<sub>j</sub>",
                     "–": "-", "—": "-", "‑": "-"}.items():
        text = text.replace(old, new)
    return text


def font_safe_text(text: str, widths: dict[int, float]) -> str:
    """Return normalized markup, rejecting characters the embedded font lacks."""
    text = supported_glyphs(text)
    visible = html.unescape(re.sub(r"<[^>]*>", "", text))
    missing = sorted({char for char in visible if not char.isspace() and ord(char) not in widths})
    if missing:
        raise ValueError(f"PDF font lacks visible characters: {missing!r}")
    return text
