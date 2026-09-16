import logging
import os
import re
import time

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

NAME, EMAIL, WEBSITE, DETAILS = range(4)
SUBMIT_COOLDOWN = 60
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MENU = ReplyKeyboardMarkup(
    [
        ["Request a quote"],
        ["Services", "Pricing"],
        ["Contact a person"],
    ],
    resize_keyboard=True,
)

SERVICES_TEXT = (
    "WP Care can help with WordPress setup, hosting and domain basics, "
    "backups, updates, diagnostics and small technical fixes."
)

PRICING_TEXT = (
    "Pricing depends on the website and the scope of support. "
    "Use Request a quote and describe what you need."
)


def text_limit(value, limit=1200):
    return value.strip()[:limit]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Hello. I can help you contact WP Care. Choose an option:",
        reply_markup=MENU,
    )
    return ConversationHandler.END


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text

    if choice == "Request a quote":
        await update.message.reply_text(
            "Great. What is your name?",
            reply_markup=ReplyKeyboardRemove(),
        )
        return NAME

    if choice == "Services":
        await update.message.reply_text(SERVICES_TEXT, reply_markup=MENU)
        return ConversationHandler.END

    if choice == "Pricing":
        await update.message.reply_text(PRICING_TEXT, reply_markup=MENU)
        return ConversationHandler.END

    if choice == "Contact a person":
        await update.message.reply_text(
            "Send a request through the quote form, and a person will reply to you.",
            reply_markup=MENU,
        )
        return ConversationHandler.END

    await update.message.reply_text("Please choose an option from the menu.", reply_markup=MENU)
    return ConversationHandler.END


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
    await update.message.reply_text(
        "What is your website URL? You can send Skip if you do not have one."
    )
    return WEBSITE


async def get_website(update: Update, context: ContextTypes.DEFAULT_TYPE):
    website = text_limit(update.message.text, 300)
    context.user_data["website"] = "" if website.lower() == "skip" else website
    await update.message.reply_text("Briefly describe what you need help with.")
    return DETAILS


async def get_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = time.monotonic()
    last_submit = context.user_data.get("last_submit", 0)

    if now - last_submit < SUBMIT_COOLDOWN:
        await update.message.reply_text(
            "Please wait a moment before sending another request.",
            reply_markup=MENU,
        )
        return ConversationHandler.END

    context.user_data["last_submit"] = now
    user = update.effective_user
    data = context.user_data
    website = data.get("website") or "Not provided"
    username = f"@{user.username}" if user and user.username else "No username"
    chat_id = update.effective_chat.id

    message = (
        "New WP Care request\n\n"
        f"Name: {data.get('name', 'Not provided')}\n"
        f"Email: {data.get('email', 'Not provided')}\n"
        f"Website: {website}\n"
        f"Telegram: {username}\n"
        f"Chat ID: {chat_id}\n\n"
        f"Request:\n{text_limit(update.message.text)}"
    )

    try:
        admin_chat_id = int(os.environ["TELEGRAM_ADMIN_CHAT_ID"])
        await context.bot.send_message(chat_id=admin_chat_id, text=message)
    except (KeyError, ValueError):
        logger.error("TELEGRAM_ADMIN_CHAT_ID is missing or invalid")
        await update.message.reply_text(
            "The request form is not configured yet. Please email wp-care@taldav.com.",
            reply_markup=MENU,
        )
        return ConversationHandler.END
    except Exception:
        logger.exception("Could not forward request")
        await update.message.reply_text(
            "The request could not be sent. Please email wp-care@taldav.com.",
            reply_markup=MENU,
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Thank you. Your request was sent. We will contact you after reviewing it.",
        reply_markup=MENU,
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Request cancelled.", reply_markup=MENU)
    return ConversationHandler.END


def build_application():
    application = Application.builder().token(os.environ["TELEGRAM_BOT_TOKEN"]).build()

    conversation = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Request a quote$"), menu)],
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
    application.add_handler(conversation)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu))
    return application


if __name__ == "__main__":
    build_application().run_polling(allowed_updates=Update.ALL_TYPES)
