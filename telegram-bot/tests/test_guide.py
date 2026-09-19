import unittest

from guide import language_buttons, language_code, menu_buttons, topic_text


class GuideTest(unittest.TestCase):
    def test_language_buttons(self):
        buttons = language_buttons()
        self.assertEqual(language_code(buttons[0]), "en")
        self.assertEqual(language_code(buttons[1]), "ru")

    def test_menu_has_all_actions(self):
        english = menu_buttons("en")
        russian = menu_buttons("ru")
        self.assertEqual(len(english), 5)
        self.assertEqual(len(russian), 5)
        self.assertNotEqual(english[0][0], russian[0][0])

    def test_topic_text_has_link(self):
        self.assertIn("https://", topic_text("en", "services"))
        self.assertIn("https://", topic_text("ru", "services"))


if __name__ == "__main__":
    unittest.main()
