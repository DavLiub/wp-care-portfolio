import logging
import os
import re
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from guide import DATA, menu_actions, topic_text

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

NAME, EMAIL, WEBSITE, DETAILS = range(4)
SUBMIT_COOLDOWN = 60
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def language_of(context):
    value = context.user_data.get("language", "en")
    return value if value in DATA else "en"


def menu_markup(language):
    rows = menu_actions(language)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text, callback_data=action) for text, action in row]
        for row in rows
    ])


def language_markup():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("English", callback_data="language:en"),
        InlineKeyboardButton(DATA["ru"]["messages"]["language_name"], callback_data="language:ru"),
    ]])


def text_limit(value, limit=1200):
    return value.strip()[:limit]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Choose language / \u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u044f\u0437\u044b\u043a:",
        reply_markup=language_markup(),
    )
    return ConversationHandler.END


async def choose_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = query.data.split(":", 1)[1]
    context.user_data["language"] = language
    await query.edit_message_text(
        DATA[language]["messages"]["welcome"],
        reply_markup=menu_markup(language),
    )
    return ConversationHandler.END


async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=language_markup())
    return ConversationHandler.END


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Choose language / \u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u044f\u0437\u044b\u043a:",
        reply_markup=language_markup(),
    )
    return ConversationHandler.END


async def show_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = language_of(context)
    action = query.data
    if action == "language":
        return await change_language(update, context)
    if action == "quote":
        return await begin_quote(update, context)
    await query.edit_message_text(
        topic_text(language, action),
        reply_markup=menu_markup(language),
    )
    return ConversationHandler.END


async def unknown_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    language = language_of(context)
    await update.message.reply_text(
        DATA[language]["messages"]["unknown"],
        reply_markup=menu_markup(language),
    )
    return ConversationHandler.END


async def begin_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Great. What is your name?")
    else:
        await update.message.reply_text("Great. What is your name?")
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = text_limit(update.message.text, 120)
    await update.message.reply_text("What email address should we use?")
    return EMAIL


async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = text_limit(update.message.text, 160)
    if not EMAIL_PATTERN.match(email):
        await update.message.reply_text("That email does not look valid. Please enter it again.")
        return EMAIL
    context.user_data["email"] = email
    await update.message.reply_text("What is your website URL? You can send Skip if you do not have one.")
    return WEBSITE


async def get_website(update: Update, context: ContextTypes.DEFAULT_TYPE):
    website = text_limit(update.message.text, 300)
    context.user_data["website"] = "" if website.lower() in ("skip", "\u043f\u0440\u043e\u043f\u0443\u0441\u0442\u0438\u0442\u044c") else website
    await update.message.reply_text("Briefly describe what you need help with.")
    return DETAILS


async def get_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = time.monotonic()
    if now - context.user_data.get("last_submit", 0) < SUBMIT_COOLDOWN:
        await update.message.reply_text("Please wait a moment before sending another request.")
        return ConversationHandler.END
    context.user_data["last_submit"] = now
    data = context.user_data
    user = update.effective_user
    website = data.get("website") or "Not provided"
    username = f"@{user.username}" if user and user.username else "No username"
    message = (
        "New WP Care request\n\n"
        f"Language: {language_of(context)}\n"
        f"Name: {data.get('name', 'Not provided')}\n"
        f"Email: {data.get('email', 'Not provided')}\n"
        f"Website: {website}\n"
        f"Telegram: {username}\n"
        f"Chat ID: {update.effective_chat.id}\n\n"
        f"Request:\n{text_limit(update.message.text)}"
    )
    try:
        admin_chat_id = int(os.environ["TELEGRAM_ADMIN_CHAT_ID"])
        await context.bot.send_message(chat_id=admin_chat_id, text=message)
    except (KeyError, ValueError):
        logger.error("TELEGRAM_ADMIN_CHAT_ID is missing or invalid")
        await update.message.reply_text("The request form is not configured yet. Please email wp-care@taldav.com.")
        return ConversationHandler.END
    except Exception:
        logger.exception("Could not forward request")
        await update.message.reply_text("The request could not be sent. Please email wp-care@taldav.com.")
        return ConversationHandler.END
    await update.message.reply_text("Thank you. Your request was sent. We will contact you.")
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    language = language_of(context)
    context.user_data.clear()
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(DATA[language]["messages"]["cancelled"], reply_markup=menu_markup(language))
    else:
        await update.message.reply_text(DATA[language]["messages"]["cancelled"], reply_markup=menu_markup(language))
    return ConversationHandler.END


def build_application():
    application = Application.builder().token(os.environ["TELEGRAM_BOT_TOKEN"]).build()
    conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(begin_quote, pattern="^quote$")],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            WEBSITE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_website)],
            DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_details)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("language", language_command))
    application.add_handler(CallbackQueryHandler(choose_language, pattern="^language:(en|ru)$"))
    application.add_handler(conversation)
    application.add_handler(CallbackQueryHandler(show_topic))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_text))
    return application


if __name__ == "__main__":
    build_application().run_polling(allowed_updates=Update.ALL_TYPES)
