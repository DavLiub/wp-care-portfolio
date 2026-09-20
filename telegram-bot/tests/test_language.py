import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
LANGUAGES = ("en", "ru")
TOPICS = ("services", "pricing", "process", "limits", "contact")


def read_json(language, name):
    path = ROOT / "knowledge" / language / f"{name}.json"
    with path.open(encoding="utf-8") as file:
        return json.load(file)


class LanguageTest(unittest.TestCase):
    def test_both_languages_are_available(self):
        for language in LANGUAGES:
            messages = read_json(language, "messages")
            self.assertEqual(messages["language"], language)
            self.assertTrue(messages["language_name"])

    def test_both_languages_have_same_topics(self):
        english = set(read_json("en", "topics"))
        russian = set(read_json("ru", "topics"))
        self.assertEqual(english, set(TOPICS))
        self.assertEqual(russian, set(TOPICS))

    def test_language_menu_labels_are_distinct(self):
        english = read_json("en", "messages")
        russian = read_json("ru", "messages")
        self.assertNotEqual(english["language_name"], russian["language_name"])

    def test_russian_text_is_preserved(self):
        text = read_json("ru", "topics")["services"]["text"]
        self.assertIn("WordPress", text)
        self.assertGreater(len(text), 10)

    def test_russian_scenario_text_is_readable(self):
        messages = read_json("ru", "messages")
        pricing = read_json("ru", "pricing")
        process = read_json("ru", "process")
        for value in (messages["ask_name"], messages["back"], messages["cancel"],
                      pricing["intro"], process["intro"]):
            self.assertTrue(any(0x0400 <= ord(char) <= 0x04FF for char in value))
        for value in messages.values():
            if isinstance(value, str):
                self.assertNotIn("???", value)
        for section in (pricing, process):
            self.assertEqual(set(section["choices"]),
                             {"one_time", "content", "technical", "custom"})
            for choice in section["choices"].values():
                self.assertNotIn("???", choice["label"] + choice["text"])

    def test_text_from_other_language_is_accepted(self):
        samples = (
            "\u041c\u043d\u0435 \u043d\u0443\u0436\u0435\u043d \u0441\u0430\u0439\u0442",
            "I need help with my website",
            "\u041d\u0443\u0436\u0435\u043d WordPress site",
        )
        for value in samples:
            self.assertEqual(value.strip(), value)
            self.assertTrue(value.strip())
