import json
from pathlib import Path


ROOT = Path(__file__).parent
LANGUAGES = ("en", "ru")
DATA = {}


def load_data():
    for language in LANGUAGES:
        folder = ROOT / "knowledge" / language
        DATA[language] = {}
        for path in folder.glob("*.json"):
            with path.open(encoding="utf-8") as file:
                DATA[language][path.stem] = json.load(file)


load_data()


def language_code(label):
    return "ru" if label.casefold() == DATA["ru"]["messages"]["language_name"].casefold() else "en"


def language_buttons():
    return ["English", DATA["ru"]["messages"]["language_name"]]


def menu_buttons(language):
    messages = DATA[language]["messages"]
    return [
        [messages["quote"]],
        [messages["services"], messages["pricing"]],
        [messages["process"], messages["limits"]],
        [messages["contact"]],
        [messages["language_menu"]],
    ]


def topic_text(language, topic):
    item = DATA[language]["topics"][topic]
    return item["text"] + ("\n\n" + item["url"] if item.get("url") else "")
