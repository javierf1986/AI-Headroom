from __future__ import annotations

import re
import unicodedata


_MOJIBAKE_MAP = {
    "Â¡": "¡",
    "Â¿": "¿",
    "â€™": "'",
    "â€œ": '"',
    "â€\x9d": '"',
    "â€“": "-",
    "â€”": "-",
    "â€¦": "...",
    "≤": "ó",
    "≥": "ú",
    "ß": "á",
    "∂": "ñ",
    "æ": "í",
    "ø": "é",
    "Ã¡": "á",
    "Ã©": "é",
    "Ã­": "í",
    "Ã³": "ó",
    "Ãº": "ú",
    "Ã±": "ñ",
    "Ã\x81": "Á",
    "Ã‰": "É",
    "Ã\x8d": "Í",
    "Ã“": "Ó",
    "Ãš": "Ú",
    "Ã‘": "Ñ",
    "┐": "¿",
    "·": "ú",
    "φ": "í",
    "Θ": "é",
    "ⁿ": "ü",
}

_MOJIBAKE_HINTS = re.compile(r"[ÃÂâ€™â€œâ€\x9d≤≥ß∂æø┐·φΘⁿ]")


def _mojibake_score(text: str) -> int:
    return len(_MOJIBAKE_HINTS.findall(text))


def normalize_text_encoding(text: str) -> str:
    if not text:
        return ""

    normalized = unicodedata.normalize("NFC", text)

    if _mojibake_score(normalized) > 0:
        try:
            candidate = normalized.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
            if candidate and _mojibake_score(candidate) < _mojibake_score(normalized):
                normalized = candidate
        except Exception:
            pass

    for bad, good in _MOJIBAKE_MAP.items():
        normalized = normalized.replace(bad, good)

    normalized = normalized.replace("Â", "")
    normalized = normalized.replace("Ã", "")
    normalized = unicodedata.normalize("NFC", normalized)
    return normalized


def has_mojibake(text: str) -> bool:
    return bool(text) and _mojibake_score(text) > 0
