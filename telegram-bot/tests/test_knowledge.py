import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
LANGUAGES = ("en", "ru")


class KnowledgeTest(unittest.TestCase):
    def test_files_exist(self):
        for language in LANGUAGES:
            self.assertTrue((ROOT / "knowledge" / language / "messages.json").exists())
            self.assertTrue((ROOT / "knowledge" / language / "topics.json").exists())

    def test_files_are_valid_json(self):
        for path in (ROOT / "knowledge").glob("*/*.json"):
            with path.open(encoding="utf-8") as file:
                self.assertIsInstance(json.load(file), dict)

