import logging
import os
import sys

import requests


_LOGGER = logging.getLogger(__name__)
_OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b-instruct-q5_0")

_DUTCH = ['het', 'een', 'van', 'de', 'is', 'te', 'op', 'dat', 'met', 'voor',
          'woning', 'appartement', 'slaapkamer', 'badkamer', 'keuken', 'tuin']
_FRENCH = ['le', 'la', 'les', 'un', 'une', 'à', 'et', 'est', 'dans',
           'maison', 'appartement', 'chambre', 'salle', 'cuisine', 'jardin']
_ENGLISH = ['the', 'a', 'an', 'of', 'is', 'in', 'to', 'and', 'with', 'for',
            'house', 'apartment', 'bedroom', 'bathroom', 'kitchen', 'garden']


def _detect_language(text):
    t = text.lower()
    nl = sum(1 for w in _DUTCH if f' {w} ' in f' {t} ')
    fr = sum(1 for w in _FRENCH if f' {w} ' in f' {t} ')
    en = sum(1 for w in _ENGLISH if f' {w} ' in f' {t} ')
    if en > nl and en > fr:
        return "en"
    if fr > nl:
        return "fr"
    return "nl"


def _ollama_available():
    return sys.platform == "darwin" or os.getenv("OLLAMA_BASE_URL")


PREAMBLE_PATTERNS = [
    "here's the translation",
    "here is the translation",
    "translation:",
    "translated text:",
    "english translation:",
    "dutch to english:",
    "french to english:",
]


def _strip_preamble(text):
    lower = text.lower()
    for pattern in PREAMBLE_PATTERNS:
        idx = lower.find(pattern)
        if idx != -1:
            after = text[idx + len(pattern):].lstrip(" :\n\r-–")
            if after:
                return after
    return text


def _ollama_translate(text, src, target):
    import time
    prompt = (
        f"Translate from {src} to {target}. Reply with ONLY the translation, no explanations.\n\n"
        f"{text}"
    )
    preview = text[:80].replace("\n", " ")
    print(f"[translator] {src}→{target} ({len(text)} chars): {preview}…")
    t0 = time.monotonic()
    try:
        response = requests.post(
            f"{_OLLAMA_BASE_URL}/api/chat",
            json={
                "model": _OLLAMA_MODEL,
                "stream": False,
                "options": {"temperature": 0},
                "messages": [
                    {"role": "system", "content": "You are a precise translation engine."},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=60,
        )
        response.raise_for_status()
        translated = response.json().get("message", {}).get("content", "").strip()
        translated = _strip_preamble(translated)
        elapsed = time.monotonic() - t0
        if translated:
            result_preview = translated[:80].replace("\n", " ")
            print(f"[translator] done in {elapsed:.1f}s: {result_preview}…")
        return translated or None
    except requests.RequestException as exc:
        _LOGGER.warning("Ollama translation unavailable at %s: %s", _OLLAMA_BASE_URL, exc)
    except Exception:
        _LOGGER.exception("Ollama translation failed for %s -> %s", src, target)
    return None


class PropertyTranslator:
    def prepare_description(self, description):
        if not description:
            return {"original": "", "translated": "", "detected_language": "unknown"}
        return {
            "original": description,
            "translated": "",
            "detected_language": _detect_language(description),
        }

    def translate_property_description(self, description, language="auto", target_language="en"):
        if not description:
            return {"original": "", "translated": "", "detected_language": "unknown"}

        detected = language if language != "auto" else _detect_language(description)

        if detected == target_language:
            return {"original": description, "translated": description, "detected_language": detected}

        translated = _ollama_translate(description, detected, target_language) if _ollama_available() else None
        return {
            "original": description,
            "translated": translated or "",
            "detected_language": detected,
        }
