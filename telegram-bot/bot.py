import logging
import os
import re
import time
from urllib.parse import urlsplit

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    ApplicationHandlerStop,
    TypeHandler,
    filters,
)

from guide import (DATA, SELECT_STEPS, choice_text, faq_text, find_question, menu_actions,
                   section_text, select_plan, select_summary, select_text, topic_text)

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

NAME, EMAIL, WEBSITE, DETAILS, REVIEW = range(5)
PICK = 5
SUBMIT_COOLDOWN = 60
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


async def edit_view(query, text, reply_markup):
    try:
        await query.edit_message_text(text, reply_markup=reply_markup)
    except BadRequest as error:
        if "message is not modified" not in str(error).lower():
            raise


def language_of(context):
    value = context.user_data.get("language", "en")
    return value if value in DATA else "en"


def menu_markup(language):
    rows = menu_actions(language)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text, callback_data=action) for text, action in row]
        for row in rows
    ])


def section_markup(language, section):
    choices = DATA[language][section]["choices"]
    rows = [
        [InlineKeyboardButton(item["label"], callback_data=f"{section}:{choice}")]
        for choice, item in choices.items()
    ]
    rows.append([InlineKeyboardButton(DATA[language]["messages"]["home"], callback_data="home")])
    return InlineKeyboardMarkup(rows)


def choice_markup(language, section, choice):
    messages = DATA[language]["messages"]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(messages["start_request"], callback_data=f"quote:{section}:{choice}")],
        [InlineKeyboardButton(messages["back_to_options"], callback_data=section)],
        [InlineKeyboardButton(messages["home"], callback_data="home")],
    ])


def detail_markup(language):
    messages = DATA[language]["messages"]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(messages["recommend"], callback_data="recommend")],
        [InlineKeyboardButton(messages["quote"], callback_data="quote")],
        [InlineKeyboardButton(messages["home"], callback_data="home")],
    ])


def faq_markup(language, group=None, question=None):
    messages = DATA[language]["messages"]
    faq = DATA[language]["faq"]
    if question:
        group = faq["questions"][question]["group"]
        rows = [
            [InlineKeyboardButton(messages["recommend"], callback_data="recommend")],
            [InlineKeyboardButton(messages["quote"], callback_data="quote")],
            [InlineKeyboardButton(messages["pricing"], callback_data="pricing")],
            [InlineKeyboardButton(messages["faq_back"], callback_data="faq:" + group)],
        ]
    elif group:
        rows = [[InlineKeyboardButton(item["label"], callback_data="faq:" + group + ":" + key)]
                for key, item in faq["questions"].items() if item["group"] == group]
        rows.append([InlineKeyboardButton(messages["faq_groups"], callback_data="faq")])
    else:
        rows = [[InlineKeyboardButton(item["label"], callback_data="faq:" + key)]
                for key, item in faq["groups"].items()]
    rows.append([InlineKeyboardButton(messages["home"], callback_data="home")])
    return InlineKeyboardMarkup(rows)


async def show_faq(update, context):
    language = language_of(context)
    faq = DATA[language]["faq"]
    parts = update.callback_query.data.split(":")
    group = parts[1] if len(parts) >= 2 else None
    question = parts[2] if len(parts) == 3 else None
    if len(parts) > 3 or (group and group not in faq["groups"]):
        return await home(update, context)
    if question and (question not in faq["questions"] or faq["questions"][question]["group"] != group):
        return await home(update, context)
    text = faq_text(language, question) if question else (
        faq["groups"][group]["label"] if group else faq["intro"])
    await update.callback_query.answer()
    await edit_view(update.callback_query, text, faq_markup(language, group, question))
    return ConversationHandler.END


def select_markup(language, answers, step):
    messages = DATA[language]["messages"]
    selection = DATA[language]["selection"]
    if step < len(SELECT_STEPS):
        key = SELECT_STEPS[step]
        rows = [[InlineKeyboardButton(label, callback_data=f"recommend:{key}:{value}")]
                for value, label in selection["questions"][key]["options"].items()]
    else:
        plan, reason = select_plan(answers)
        rows = [
            [InlineKeyboardButton(messages["start_request"], callback_data="quote:selection:" + plan)],
            [InlineKeyboardButton(messages["pricing"], callback_data="pricing:" + plan)],
            [InlineKeyboardButton(selection["retry"], callback_data="recommend")],
        ]
    if step:
        rows.append([InlineKeyboardButton(messages["back"], callback_data="recommend:back")])
    rows.append([
        InlineKeyboardButton(messages["cancel"], callback_data="quote:cancel"),
        InlineKeyboardButton(messages["home"], callback_data="home"),
    ])
    return InlineKeyboardMarkup(rows)


async def show_select(update, context):
    language = language_of(context)
    answers = context.user_data.get("select_answers", {})
    step = context.user_data.get("select_step", 0)
    selection = DATA[language]["selection"]
    if step == len(SELECT_STEPS):
        text = select_text(language, answers)
    else:
        text = selection["questions"][SELECT_STEPS[step]]["text"]
        if step == 0:
            text = selection["intro"] + "\n\n" + text
    markup = select_markup(language, answers, step)
    if update.callback_query:
        await update.callback_query.answer()
        await edit_view(update.callback_query, text, markup)
    else:
        await update.message.reply_text(text, reply_markup=markup)
    return PICK


async def begin_select(update, context):
    clear_quote(context)
    context.user_data["select_answers"] = {}
    context.user_data["select_step"] = 0
    return await show_select(update, context)


async def answer_select(update, context):
    data = context.user_data
    step = data.get("select_step", 0)
    answers = data.setdefault("select_answers", {})
    parts = update.callback_query.data.split(":")
    if parts == ["recommend", "back"] and step:
        step -= 1
        for key in SELECT_STEPS[step:]:
            answers.pop(key, None)
        data["select_step"] = step
    elif len(parts) == 3 and step < len(SELECT_STEPS):
        key, value = parts[1:]
        options = DATA[language_of(context)]["selection"]["questions"][SELECT_STEPS[step]]["options"]
        # Old or forged buttons must not skip questions or change earlier answers.
        if key == SELECT_STEPS[step] and value in options:
            answers[key] = value
            data["select_step"] = step + 1
    return await show_select(update, context)


def clear_quote(context):
    language = context.user_data.get("language")
    last_submit = context.user_data.get("last_submit")
    context.user_data.clear()
    if language in DATA:
        context.user_data["language"] = language
    if last_submit is not None:
        context.user_data["last_submit"] = last_submit


def quote_markup(language, state=None):
    messages = DATA[language]["messages"]
    rows = []
    if state == WEBSITE:
        rows.append([InlineKeyboardButton(messages["skip"], callback_data="quote:skip")])
    if state == REVIEW:
        rows.append([InlineKeyboardButton(messages["confirm"], callback_data="quote:send")])
    return InlineKeyboardMarkup(rows + [[
        InlineKeyboardButton(messages["back"], callback_data="quote:back"),
        InlineKeyboardButton(messages["cancel"], callback_data="quote:cancel"),
    ], [
        InlineKeyboardButton(messages["home"], callback_data="home"),
    ]])


def quote_message(context, key):
    return DATA[language_of(context)]["messages"][key]


async def show_prompt(update, context, key):
    language = language_of(context)
    text = quote_message(context, key)
    origin = context.user_data.get("quote_origin")
    if key == "ask_name" and origin:
        section, choice = origin.split(":")
        text = DATA[language][section]["choices"][choice]["label"] + "\n\n" + text
    if key == "ask_name" and context.user_data.get("quote_selection"):
        text = select_summary(language, context.user_data["quote_selection"]) + "\n\n" + text
    markup = quote_markup(language, context.user_data.get("quote_state"))
    if update.callback_query:
        await update.callback_query.answer()
        await edit_view(update.callback_query,text, reply_markup=markup)
    else:
        await update.message.reply_text(text, reply_markup=markup)


def language_markup():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("English", callback_data="language:en"),
            InlineKeyboardButton(DATA["ru"]["messages"]["language_name"], callback_data="language:ru"),
        ],
        [InlineKeyboardButton(DATA["en"]["messages"]["home"] + " / " + DATA["ru"]["messages"]["home"],
                              callback_data="home")],
    ])


def text_limit(value, limit=1200):
    return value.strip()[:limit]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_quote(context)
    await update.message.reply_text(
        "Choose language / \u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u044f\u0437\u044b\u043a:",
        reply_markup=language_markup(),
    )
    return ConversationHandler.END


async def choose_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = query.data.split(":", 1)[1]
    clear_quote(context)
    context.user_data["language"] = language
    await edit_view(query,
        DATA[language]["messages"]["welcome"],
        reply_markup=menu_markup(language),
    )
    return ConversationHandler.END


async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_reply_markup(reply_markup=language_markup())
    except BadRequest as error:
        if "message is not modified" not in str(error).lower():
            raise
    return ConversationHandler.END


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_quote(context)
    await update.message.reply_text(
        "Choose language / \u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u044f\u0437\u044b\u043a:",
        reply_markup=language_markup(),
    )
    return ConversationHandler.END


async def home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    language = language_of(context)
    clear_quote(context)
    query = update.callback_query
    await query.answer()
    await edit_view(query,
        DATA[language]["messages"]["welcome"],
        reply_markup=menu_markup(language),
    )
    return ConversationHandler.END


async def show_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    language = language_of(context)
    action = query.data
    if action == "faq" or action.startswith("faq:"):
        return await show_faq(update, context)
    if action == "home":
        return await home(update, context)
    if action == "language":
        return await change_language(update, context)
    if action == "quote":
        return await begin_quote(update, context)
    if action.startswith("quote:"):
        return await home(update, context)
    if action in ("pricing", "process"):
        await query.answer()
        await edit_view(query,
            section_text(language, action),
            reply_markup=section_markup(language, action),
        )
        return ConversationHandler.END
    if ":" in action:
        section, choice = action.split(":", 1)
        if section in ("pricing", "process") and choice in DATA[language][section]["choices"]:
            await query.answer()
            await edit_view(query,
                choice_text(language, section, choice),
                reply_markup=choice_markup(language, section, choice),
            )
            return ConversationHandler.END
        return await home(update, context)
    if action not in DATA[language]["topics"]:
        return await home(update, context)
    await query.answer()
    await edit_view(query,
        topic_text(language, action),
        reply_markup=detail_markup(language),
    )
    return ConversationHandler.END


async def leave_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_quote(context)
    return await show_topic(update, context)


async def unknown_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    language = language_of(context)
    question = find_question(update.message.text)
    if question:
        await update.message.reply_text(faq_text(language, question),
                                        reply_markup=faq_markup(language, question=question))
    else:
        await update.message.reply_text(
            DATA[language]["messages"]["unknown"], reply_markup=menu_markup(language))
    return ConversationHandler.END


async def begin_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    language = language_of(context)
    action = update.callback_query.data if update.callback_query else "quote"
    selected = None
    parts = action.split(":")
    if len(parts) == 3 and parts[1] == "selection":
        answers = context.user_data.get("select_answers", {})
        if (context.user_data.get("select_step") != len(SELECT_STEPS)
                or parts[2] != select_plan(answers)[0]):
            return await home(update, context)
        selected = answers.copy()
    clear_quote(context)
    if selected:
        context.user_data["quote_selection"] = selected
        context.user_data["quote_origin"] = "pricing:" + parts[2]
    if len(parts) == 3 and parts[1] in ("pricing", "process"):
        section, choice = parts[1:]
        if choice in DATA[language][section]["choices"]:
            context.user_data["quote_origin"] = f"{section}:{choice}"
    context.user_data["quote_state"] = NAME
    await show_prompt(update, context, "ask_name")
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = update.message.text.strip()
    if not value or len(value) > 120:
        await show_prompt(update, context, "invalid_name")
        return NAME
    context.user_data["name"] = value
    context.user_data["quote_state"] = EMAIL
    await show_prompt(update, context, "ask_email")
    return EMAIL


async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    if len(email) > 160 or not EMAIL_PATTERN.fullmatch(email):
        await show_prompt(update, context, "invalid_email")
        return EMAIL
    context.user_data["email"] = email
    context.user_data["quote_state"] = WEBSITE
    await show_prompt(update, context, "ask_website")
    return WEBSITE


async def get_website(update: Update, context: ContextTypes.DEFAULT_TYPE):
    website = update.message.text.strip() if update.message else "skip"
    skip = quote_message(context, "skip").casefold()
    if website.casefold() in ("skip", "пропустить", skip):
        website = ""
    else:
        website = website if "://" in website else "https://" + website
        try:
            parsed = urlsplit(website)
            valid = (parsed.scheme in ("https", "http") and parsed.hostname
                     and "." in parsed.hostname and not parsed.username
                     and not parsed.password and not any(c.isspace() for c in website)
                     and len(website) <= 300)
            parsed.port
        except ValueError:
            valid = False
        if not valid:
            await show_prompt(update, context, "invalid_website")
            return WEBSITE
    context.user_data["website"] = website
    context.user_data["quote_state"] = DETAILS
    await show_prompt(update, context, "ask_details")
    return DETAILS


def review_text(context):
    data = context.user_data
    messages = DATA[language_of(context)]["messages"]
    origin = data.get("quote_origin")
    service = messages["general_request"]
    if origin:
        section, choice = origin.split(":")
        service = DATA[language_of(context)][section]["choices"][choice]["label"]
    if data.get("quote_selection"):
        service += "\n" + select_summary(language_of(context), data["quote_selection"])
    return messages["review"].format(
        service=service, name=data["name"], email=data["email"],
        website=data.get("website") or messages["no_website"], details=data["details"])


async def show_review(update, context):
    context.user_data["quote_state"] = REVIEW
    markup = quote_markup(language_of(context), REVIEW)
    if update.callback_query:
        await update.callback_query.answer()
        await edit_view(update.callback_query, review_text(context), markup)
    else:
        await update.message.reply_text(review_text(context), reply_markup=markup)
    return REVIEW


async def get_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    details = update.message.text.strip()
    if not details or len(details) > 1200:
        await show_prompt(update, context, "invalid_details")
        return DETAILS
    context.user_data["details"] = details
    return await show_review(update, context)


async def send_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    now = time.monotonic()
    last_submit = context.user_data.get("last_submit")
    if last_submit is not None and now - last_submit < SUBMIT_COOLDOWN:
        language = language_of(context)
        await edit_view(update.callback_query, quote_message(context, "cooldown"), quote_markup(language, REVIEW))
        return REVIEW
    data = context.user_data
    user = update.effective_user
    website = data.get("website") or "Not provided"
    username = f"@{user.username}" if user and user.username else "No username"
    origin = data.get("quote_origin")
    section, choice = origin.split(":") if origin else (None, None)
    service = DATA[language_of(context)][section]["choices"][choice]["label"] if origin else "General request"
    selection = ("Support selection:\n" + select_summary(language_of(context), data["quote_selection"]) + "\n\n"
                 if data.get("quote_selection") else "")
    message = (
        "New WP Care request\n\n"
        f"Language: {language_of(context)}\n"
        f"Service: {service}\n"
        f"Name: {data.get('name', 'Not provided')}\n"
        f"Email: {data.get('email', 'Not provided')}\n"
        f"Website: {website}\n"
        f"Telegram: {username}\n"
        f"Chat ID: {update.effective_chat.id}\n\n"
        + selection + f"Request:\n{data['details']}"
    )
    try:
        admin_chat_id = int(os.environ["TELEGRAM_ADMIN_CHAT_ID"])
        await context.bot.send_message(chat_id=admin_chat_id, text=message)
    except (KeyError, ValueError):
        logger.error("TELEGRAM_ADMIN_CHAT_ID is missing or invalid")
        language = language_of(context)
        await edit_view(update.callback_query, quote_message(context, "not_configured"), quote_markup(language, REVIEW))
        return REVIEW
    except Exception:
        logger.error("Could not forward request")
        language = language_of(context)
        await edit_view(update.callback_query, quote_message(context, "send_failed"), quote_markup(language, REVIEW))
        return REVIEW
    language = language_of(context)
    context.user_data["last_submit"] = now
    clear_quote(context)
    await edit_view(update.callback_query, quote_message(context, "sent"), menu_markup(language))
    return ConversationHandler.END


async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("quote_state", NAME)
    if state == NAME and context.user_data.get("quote_selection"):
        answers = context.user_data["quote_selection"].copy()
        clear_quote(context)
        context.user_data.update(select_answers=answers, select_step=len(SELECT_STEPS))
        return await show_select(update, context)
    if state == NAME:
        origin = context.user_data.get("quote_origin")
        language = language_of(context)
        clear_quote(context)
        if origin:
            section, choice = origin.split(":")
            await update.callback_query.answer()
            await edit_view(update.callback_query,
                choice_text(language, section, choice),
                reply_markup=choice_markup(language, section, choice),
            )
        else:
            await home(update, context)
        return ConversationHandler.END
    previous = {EMAIL: (NAME, "ask_name"), WEBSITE: (EMAIL, "ask_email"), DETAILS: (WEBSITE, "ask_website"), REVIEW: (DETAILS, "ask_details")}
    state, prompt = previous[state]
    context.user_data["quote_state"] = state
    await show_prompt(update, context, prompt)
    return state


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    language = language_of(context)
    clear_quote(context)
    if update.callback_query:
        await update.callback_query.answer()
        await edit_view(update.callback_query,DATA[language]["messages"]["cancelled"], reply_markup=menu_markup(language))
    else:
        await update.message.reply_text(DATA[language]["messages"]["cancelled"], reply_markup=menu_markup(language))
    return ConversationHandler.END


async def group_notice(update, context):
    if not update.effective_chat or update.effective_chat.type != "private":
        raise ApplicationHandlerStop


async def log_error(update, context):
    # Exception text and update payloads may contain tokens or customer details.
    logger.error("Telegram handler failed: %s", type(context.error).__name__)


def build_application():
    application = Application.builder().token(os.environ["TELEGRAM_BOT_TOKEN"]).build()
    conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(begin_quote, pattern=r"^quote(?::(?:pricing|process|selection):[a-z_]+)?$"),
                      CallbackQueryHandler(begin_select, pattern="^recommend$")],
        states={
            PICK: [CallbackQueryHandler(answer_select, pattern="^recommend:"),
                   MessageHandler(filters.TEXT & ~filters.COMMAND, show_select)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            WEBSITE: [CallbackQueryHandler(get_website, pattern="^quote:skip$"), MessageHandler(filters.TEXT & ~filters.COMMAND, get_website)],
            DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_details)],
            REVIEW: [CallbackQueryHandler(send_quote, pattern="^quote:send$"),
                     MessageHandler(filters.TEXT & ~filters.COMMAND, show_review)],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("cancel", cancel),
            CommandHandler("language", language_command),
            CallbackQueryHandler(cancel, pattern="^quote:cancel$"),
            CallbackQueryHandler(back, pattern="^quote:back$"),
            CallbackQueryHandler(home, pattern="^home$"),
            CallbackQueryHandler(choose_language, pattern="^language:(en|ru)$"),
            CallbackQueryHandler(leave_quote, pattern=r"^(?:(?:services|pricing|process|limits|contact|language)(?::[a-z_]+)?|faq(?::[a-z_]+){0,2})$"),
        ],
        allow_reentry=True,
    )
    application.add_handler(TypeHandler(Update, group_notice), group=-1)
    application.add_error_handler(log_error)
    application.add_handler(conversation)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("language", language_command))
    application.add_handler(CallbackQueryHandler(choose_language, pattern="^language:(en|ru)$"))
    application.add_handler(CallbackQueryHandler(show_topic))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_text))
    return application


if __name__ == "__main__":
    build_application().run_polling(allowed_updates=Update.ALL_TYPES)
