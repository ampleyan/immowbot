import unittest
from unittest.mock import patch

from src.translator import PropertyTranslator


class PropertyTranslatorTest(unittest.TestCase):
    @patch("src.translator._mymemory_translate", return_value="Nederlandse tekst")
    def test_translates_english_to_requested_dutch(self, translate):
        result = PropertyTranslator().translate_property_description("The apartment has a garden and two bedrooms", target_language="nl")
        self.assertEqual(result["translated"], "Nederlandse tekst")
        translate.assert_called_once_with("The apartment has a garden and two bedrooms", "en", "nl")

    @patch("src.translator._mymemory_translate")
    def test_dutch_description_is_not_retranslated(self, translate):
        result = PropertyTranslator().translate_property_description("Dit is een appartement", target_language="nl")
        self.assertEqual(result["translated"], "Dit is een appartement")
        translate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
