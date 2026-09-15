import unittest
from unittest.mock import patch

from src.translator import PropertyTranslator


class PropertyTranslatorTest(unittest.TestCase):
    @patch("src.translator._ollama_translate")
    def test_prepare_description_does_not_call_ollama(self, translate):
        result = PropertyTranslator().prepare_description("Dit appartement heeft een tuin")
        self.assertEqual(result, {
            "original": "Dit appartement heeft een tuin",
            "translated": "",
            "detected_language": "nl",
        })
        translate.assert_not_called()

    @patch("src.translator._ollama_translate", return_value="English text")
    def test_translates_dutch_to_requested_english(self, translate):
        result = PropertyTranslator().translate_property_description("Dit appartement heeft een tuin", target_language="en")
        self.assertEqual(result["translated"], "English text")
        translate.assert_called_once_with("Dit appartement heeft een tuin", "nl", "en")

    @patch("src.translator._ollama_translate")
    def test_english_description_is_not_retranslated(self, translate):
        result = PropertyTranslator().translate_property_description("This is an apartment", target_language="en")
        self.assertEqual(result["translated"], "This is an apartment")
        translate.assert_not_called()

    @patch("src.translator._ollama_translate", return_value=None)
    def test_missing_translation_model_keeps_original_description(self, translate):
        result = PropertyTranslator().translate_property_description("Dit appartement heeft een tuin", target_language="en")
        self.assertEqual(result["translated"], "Dit appartement heeft een tuin")


if __name__ == "__main__":
    unittest.main()
