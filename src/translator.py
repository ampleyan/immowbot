import urllib.parse
import requests


_MYMEMORY_URL = "https://api.mymemory.translated.net/get"
_MAX_CHARS = 500

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


def _mymemory_translate(text, src, target):
    chunk = text[:_MAX_CHARS]
    try:
        r = requests.get(
            _MYMEMORY_URL,
            params={"q": chunk, "langpair": f"{src}|{target}"},
            timeout=8,
        )
        if r.status_code == 200:
            data = r.json()
            if data.get("responseStatus") == 200:
                return data["responseData"]["translatedText"]
    except Exception:
        pass
    return None


class PropertyTranslator:
    def translate_property_description(self, description, language="auto", target_language="en"):
        if not description:
            return {"original": "", "translated": "", "detected_language": "unknown"}

        detected = language if language != "auto" else _detect_language(description)

        if detected == target_language:
            return {"original": description, "translated": description, "detected_language": detected}

        translated = _mymemory_translate(description, detected, target_language)
        return {
            "original": description,
            "translated": translated or description,
            "detected_language": detected,
        }
