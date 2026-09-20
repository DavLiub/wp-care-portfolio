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


def menu_actions(language):
    messages = DATA[language]["messages"]
    return [
        [(messages["quote"], "quote")],
        [(messages["services"], "services"), (messages["pricing"], "pricing")],
        [(messages["process"], "process"), (messages["limits"], "limits")],
        [(messages["contact"], "contact")],
        [(messages["language_menu"], "language")],
    ]


def topic_text(language, topic):
    item = DATA[language]["topics"][topic]
    return item["text"] + ("\n\n" + item["url"] if item.get("url") else "")


def section_text(language, section):
    item = DATA[language][section]
    return item["intro"] + "\n\n" + item["url"]


def choice_text(language, section, choice):
    item = DATA[language][section]["choices"][choice]
    return item["label"] + "\n\n" + item["text"] + "\n\n" + DATA[language][section]["url"]
