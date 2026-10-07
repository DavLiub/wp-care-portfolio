import json
import re
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
        [messages["recommend"], messages["quote"]],
        [messages["services"], messages["pricing"]],
        [messages["process"], messages["limits"]],
        [messages["faq"], messages["contact"]],
        [messages["language_menu"]],
    ]


def menu_actions(language):
    messages = DATA[language]["messages"]
    return [
        [(messages["recommend"], "recommend"), (messages["quote"], "quote")],
        [(messages["services"], "services"), (messages["pricing"], "pricing")],
        [(messages["process"], "process"), (messages["limits"], "limits")],
        [(messages["faq"], "faq"), (messages["contact"], "contact")],
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


def normalize_question(text):
    return " ".join(re.findall(r"\w+", text.casefold().replace("ё", "е")))


def find_question(text):
    if len(text) > 500:
        return None
    query = normalize_question(text)
    matches = set()
    for data in DATA.values():
        for key, item in data["faq"]["questions"].items():
            phrases = [item["label"], *item["aliases"]]
            if any(query == normalize_question(value) for value in phrases):
                matches.add(key)
    return next(iter(matches)) if len(matches) == 1 else None


def faq_text(language, question):
    item = DATA[language]["faq"]["questions"][question]
    return item["label"] + "\n\n" + item["text"] + "\n\n" + item["url"]


SELECT_STEPS = ("mode", "need", "sites")


def select_plan(answers):
    if answers.get("sites") == "multiple":
        return "custom", "multiple"
    if answers.get("sites") == "none" or answers.get("need") == "launch":
        return "custom", "launch"
    if answers.get("need") == "custom":
        return "custom", "custom"
    if any(answers.get(key) not in DATA["en"]["selection"]["questions"][key]["options"]
           or answers.get(key) == "unsure" for key in SELECT_STEPS):
        return "custom", "unsure"
    if answers["mode"] == "one_time":
        return "one_time", "one_time"
    return ("content", "content") if answers["need"] == "content" else ("technical", "technical")


def select_summary(language, answers):
    questions = DATA[language]["selection"]["questions"]
    return "\n".join(questions[key]["label"] + ": " + questions[key]["options"][answers[key]]
                     for key in SELECT_STEPS)


def select_text(language, answers):
    selection = DATA[language]["selection"]
    plan, reason = select_plan(answers)
    label = selection["custom_label"] if plan == "custom" else DATA[language]["pricing"]["choices"][plan]["label"]
    return selection["result"].format(plan=label, reason=selection["reasons"][reason],
                                      answers=select_summary(language, answers))
