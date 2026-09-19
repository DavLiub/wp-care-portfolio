import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from telegram.ext import ConversationHandler

from bot import NAME, EMAIL, WEBSITE, DETAILS, back, begin_quote, cancel, get_details, get_email, get_name, get_website, quote_markup
from guide import DATA


class QuoteTest(unittest.TestCase):
    def setUp(self):
        self.context = SimpleNamespace(user_data={}, bot=SimpleNamespace(send_message=AsyncMock()))
        self.message = SimpleNamespace(text="", reply_text=AsyncMock())
        self.query = SimpleNamespace(answer=AsyncMock(), edit_message_text=AsyncMock())
        self.update = SimpleNamespace(message=self.message, callback_query=None,
                                      effective_user=SimpleNamespace(username="tester"),
                                      effective_chat=SimpleNamespace(id=123))

    def send_text(self, text, handler):
        self.message.text = text
        return asyncio.run(handler(self.update, self.context))

    def test_both_languages_complete_request(self):
        for language in ("en", "ru"):
            with self.subTest(language=language):
                self.setUp()
                self.context.user_data["language"] = language
                self.update.callback_query = self.query
                self.update.message = None
                self.assertEqual(asyncio.run(begin_quote(self.update, self.context)), NAME)
                self.assertEqual(self.query.edit_message_text.call_args.args[0], DATA[language]["messages"]["ask_name"])
                buttons = quote_markup(language).inline_keyboard[0]
                self.assertEqual([button.text for button in buttons],
                                 [DATA[language]["messages"]["back"], DATA[language]["messages"]["cancel"]])
                self.update.callback_query = None
                self.update.message = self.message
                self.assertEqual(self.send_text("Alex", get_name), EMAIL)
                self.assertEqual(self.send_text("bad-email", get_email), EMAIL)
                self.assertEqual(self.message.reply_text.call_args.args[0], DATA[language]["messages"]["invalid_email"])
                self.assertEqual(self.send_text("alex@example.com", get_email), WEBSITE)
                self.assertEqual(self.send_text(DATA[language]["messages"]["skip"], get_website), DETAILS)
                self.assertEqual(self.context.user_data["website"], "")
                with patch.dict(os.environ, {"TELEGRAM_ADMIN_CHAT_ID": "42"}):
                    self.assertEqual(self.send_text("Need WordPress help", get_details), ConversationHandler.END)
                self.context.bot.send_message.assert_awaited_once()
                self.assertIn("Language: " + language, self.context.bot.send_message.call_args.kwargs["text"])
                self.assertEqual(self.message.reply_text.call_args.args[0], DATA[language]["messages"]["sent"])
                self.assertEqual(self.context.user_data, {"language": language})

    def test_back_and_cancel_in_both_languages(self):
        for language in ("en", "ru"):
            with self.subTest(language=language):
                self.setUp()
                self.context.user_data.update(language=language, quote_state=DETAILS, name="Alex")
                self.update.message = None
                self.update.callback_query = self.query
                self.assertEqual(asyncio.run(back(self.update, self.context)), WEBSITE)
                self.assertEqual(self.query.edit_message_text.call_args.args[0], DATA[language]["messages"]["ask_website"])
                self.assertEqual(asyncio.run(back(self.update, self.context)), EMAIL)
                self.assertEqual(asyncio.run(back(self.update, self.context)), NAME)
                self.assertEqual(asyncio.run(back(self.update, self.context)), ConversationHandler.END)
                self.assertEqual(self.query.edit_message_text.call_args.args[0], DATA[language]["messages"]["welcome"])
                self.context.user_data["quote_state"] = NAME
                self.assertEqual(asyncio.run(cancel(self.update, self.context)), ConversationHandler.END)
                self.assertEqual(self.query.edit_message_text.call_args.args[0], DATA[language]["messages"]["cancelled"])
                self.assertEqual(self.context.user_data, {"language": language})
