import logging
import os

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


def _ollama_translate(text, src, target):
    """Translate through a local Ollama chat model."""
    prompt = (
        f"Translate the following real-estate description from {src} to {target}. "
        "Output only the translation; preserve numbers, units, names, and formatting.\n\n"
        f"{text}"
    )
    try:
        response = requests.post(
            f"{_OLLAMA_BASE_URL}/api/chat",
            json={
                "model": _OLLAMA_MODEL,
                "stream": False,
                "options": {"temperature": 0},
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a precise translation engine.",
                    },
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=60,
        )
        response.raise_for_status()
        translated = response.json().get("message", {}).get("content", "").strip()
        return translated or None
    except requests.RequestException as exc:
        _LOGGER.warning("Ollama translation unavailable at %s: %s", _OLLAMA_BASE_URL, exc)
    except Exception:
        _LOGGER.exception("Ollama translation failed for %s -> %s", src, target)
    return None


class PropertyTranslator:
    def translate_property_description(self, description, language="auto", target_language="en"):
        if not description:
            return {"original": "", "translated": "", "detected_language": "unknown"}

        detected = language if language != "auto" else _detect_language(description)

        if detected == target_language:
            return {"original": description, "translated": description, "detected_language": detected}

        translated = _ollama_translate(description, detected, target_language)
        return {
            "original": description,
            "translated": translated or description,
            "detected_language": detected,
        }
