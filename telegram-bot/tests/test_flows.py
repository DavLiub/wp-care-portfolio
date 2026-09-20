"""User journeys through the real Telegram update router, without network access."""

import asyncio
import os
import unittest
import warnings
from unittest.mock import AsyncMock, patch

from telegram import Update, User
from telegram.error import BadRequest

from bot import build_application
from guide import DATA


class FlowTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.token = patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "123456:TEST_TOKEN",
            "TELEGRAM_ADMIN_CHAT_ID": "999",
        })
        self.token.start()
        asyncio.get_running_loop().slow_callback_duration = 1.0
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="If 'per_message=False'.*",
                category=UserWarning,
            )
            self.app = build_application()
        self.bot_type = type(self.app.bot)
        self.get_me = patch.object(self.bot_type, "get_me", new_callable=AsyncMock)
        self.send = patch.object(self.bot_type, "send_message", new_callable=AsyncMock)
        self.edit = patch.object(self.bot_type, "edit_message_text", new_callable=AsyncMock)
        self.markup = patch.object(self.bot_type, "edit_message_reply_markup", new_callable=AsyncMock)
        self.answer = patch.object(self.bot_type, "answer_callback_query", new_callable=AsyncMock)
        bot_user = User(id=123456, is_bot=True, first_name="Test Bot", username="test_bot")
        self.get_me.start().return_value = bot_user
        self.send_mock = self.send.start()
        self.edit_mock = self.edit.start()
        self.markup_mock = self.markup.start()
        self.answer_mock = self.answer.start()
        await self.app.initialize()
        self.app.bot._bot_user = bot_user
        self.errors = []
        self.app.add_error_handler(self.record_error)
        self.number = 0
        self.user_id = 123

    async def asyncTearDown(self):
        await self.app.shutdown()
        self.answer.stop()
        self.markup.stop()
        self.edit.stop()
        self.send.stop()
        self.get_me.stop()
        self.token.stop()

    async def record_error(self, update, context):
        self.errors.append(context.error)

    async def send_update(self, text=None, button=None):
        self.number += 1
        user = {"id": self.user_id, "is_bot": False, "first_name": "Alex", "username": "alex"}
        message = {
            "message_id": self.number,
            "date": 1700000000,
            "chat": {"id": self.user_id, "type": "private"},
            "from": user,
        }
        if button is None:
            message["text"] = text
            if text.startswith("/"):
                message["entities"] = [{"type": "bot_command", "offset": 0, "length": len(text)}]
            data = {"update_id": self.number, "message": message}
        else:
            data = {"update_id": self.number, "callback_query": {
                "id": str(self.number), "from": user, "chat_instance": "test",
                "data": button, "message": message,
            }}
        await self.app.process_update(Update.de_json(data, self.app.bot))
        self.assertEqual(self.errors, [])

    def admin_calls(self):
        return [call for call in self.send_mock.call_args_list if call.kwargs.get("chat_id") == 999]

    async def test_complete_request_in_each_language(self):
        for language in ("en", "ru"):
            with self.subTest(language=language):
                self.user_id = 123 if language == "en" else 124
                await self.send_update("/start")
                await self.send_update(button="language:" + language)
                self.assertEqual(self.edit_mock.call_args.kwargs["text"], DATA[language]["messages"]["welcome"])
                await self.send_update(button="quote")
                self.assertEqual(self.edit_mock.call_args.kwargs["text"], DATA[language]["messages"]["ask_name"])
                await self.send_update("Alex")
                self.assertEqual(self.send_mock.call_args.kwargs["text"], DATA[language]["messages"]["ask_email"])
                await self.send_update("bad")
                self.assertEqual(self.send_mock.call_args.kwargs["text"], DATA[language]["messages"]["invalid_email"])
                await self.send_update("alex@example.com")
                await self.send_update(DATA[language]["messages"]["skip"])
                self.assertEqual(self.send_mock.call_args.kwargs["text"], DATA[language]["messages"]["ask_details"])
                await self.send_update("Need WordPress help")
                self.assertEqual(self.send_mock.call_args.kwargs["text"], DATA[language]["messages"]["sent"])
                admin = self.admin_calls()[-1].kwargs["text"]
                self.assertIn("Language: " + language, admin)
                self.assertIn("Email: alex@example.com", admin)
                self.assertIn("Request:\nNeed WordPress help", admin)
                self.assertEqual(self.app.user_data[self.user_id]["language"], language)
                self.assertIn("last_submit", self.app.user_data[self.user_id])

    async def test_back_then_cancel_in_each_language(self):
        for language in ("en", "ru"):
            with self.subTest(language=language):
                self.user_id = 123 if language == "en" else 124
                await self.send_update("/start")
                await self.send_update(button="language:" + language)
                await self.send_update(button="quote")
                await self.send_update("Alex")
                await self.send_update(button="quote:back")
                self.assertEqual(self.edit_mock.call_args.kwargs["text"], DATA[language]["messages"]["ask_name"])
                await self.send_update("New name")
                await self.send_update("alex@example.com")
                await self.send_update(button="quote:cancel")
                self.assertEqual(self.edit_mock.call_args.kwargs["text"], DATA[language]["messages"]["cancelled"])
                self.assertEqual(self.app.user_data[self.user_id], {"language": language})
                self.assertEqual(self.admin_calls(), [])
                await self.send_update(button="quote")
                self.assertEqual(self.edit_mock.call_args.kwargs["text"], DATA[language]["messages"]["ask_name"])

    async def test_back_from_first_step_returns_to_menu(self):
        await self.send_update("/start")
        await self.send_update(button="language:ru")
        await self.send_update(button="quote")
        await self.send_update(button="quote:back")
        self.assertEqual(self.edit_mock.call_args.kwargs["text"], DATA["ru"]["messages"]["welcome"])
        await self.send_update("unexpected text")
        self.assertEqual(self.send_mock.call_args.kwargs["text"], DATA["ru"]["messages"]["unknown"])

    async def test_command_cancel_and_topics(self):
        await self.send_update("/start")
        await self.send_update(button="language:en")
        await self.send_update(button="services")
        self.assertIn("https://", self.edit_mock.call_args.kwargs["text"])
        await self.send_update(button="quote")
        await self.send_update("Alex")
        await self.send_update("/cancel")
        self.assertEqual(self.send_mock.call_args.kwargs["text"], DATA["en"]["messages"]["cancelled"])
        self.assertEqual(self.app.user_data[123], {"language": "en"})
        self.assertEqual(self.admin_calls(), [])

    async def test_delivery_failure_in_each_language(self):
        for language in ("en", "ru"):
            with self.subTest(language=language):
                self.user_id = 123 if language == "en" else 124
                await self.send_update("/start")
                await self.send_update(button="language:" + language)
                await self.send_update(button="quote")
                await self.send_update("Alex")
                await self.send_update("alex@example.com")
                await self.send_update(DATA[language]["messages"]["skip"])
                async def fail_admin(*args, **kwargs):
                    if kwargs.get("chat_id") == 999:
                        raise RuntimeError("Telegram unavailable")
                self.send_mock.side_effect = fail_admin
                with patch("bot.logger.exception") as log_error:
                    await self.send_update("Need help")
                log_error.assert_called_once_with("Could not forward request")
                self.send_mock.side_effect = None
                self.assertEqual(self.send_mock.call_args.kwargs["text"], DATA[language]["messages"]["send_failed"])

    async def test_pricing_and_process_choices_in_both_languages(self):
        for language in ("en", "ru"):
            with self.subTest(language=language):
                self.user_id = 123 if language == "en" else 124
                await self.send_update("/start")
                await self.send_update(button="language:" + language)
                for section in ("pricing", "process"):
                    await self.send_update(button=section)
                    self.assertIn(DATA[language][section]["intro"], self.edit_mock.call_args.kwargs["text"])
                    buttons = self.edit_mock.call_args.kwargs["reply_markup"].inline_keyboard
                    self.assertEqual(len(buttons), 5)
                    self.assertEqual(buttons[-1][0].callback_data, "home")
                    for choice in ("one_time", "content", "technical", "custom"):
                        await self.send_update(button=section + ":" + choice)
                        item = DATA[language][section]["choices"][choice]
                        self.assertIn(item["text"], self.edit_mock.call_args.kwargs["text"])
                        actions = [
                            button.callback_data
                            for row in self.edit_mock.call_args.kwargs["reply_markup"].inline_keyboard
                            for button in row
                        ]
                        self.assertEqual(actions, ["quote:" + section + ":" + choice, section, "home"])
                        await self.send_update(button="quote:" + section + ":" + choice)
                        self.assertEqual(self.app.user_data[self.user_id]["quote_origin"],
                                         section + ":" + choice)
                        self.assertIn(DATA[language]["messages"]["ask_name"],
                                      self.edit_mock.call_args.kwargs["text"])
                        await self.send_update(button="quote:back")
                        self.assertIn(item["text"], self.edit_mock.call_args.kwargs["text"])
                        await self.send_update(button=section)
                    await self.send_update(button="home")
                    self.assertEqual(self.edit_mock.call_args.kwargs["text"], DATA[language]["messages"]["welcome"])

    async def test_choice_request_back_and_home(self):
        await self.send_update("/start")
        await self.send_update(button="language:ru")
        await self.send_update(button="pricing")
        await self.send_update(button="pricing:technical")
        await self.send_update(button="quote:pricing:technical")
        self.assertIn(DATA["ru"]["pricing"]["choices"]["technical"]["label"],
                      self.edit_mock.call_args.kwargs["text"])
        self.assertEqual(self.app.user_data[123]["quote_origin"], "pricing:technical")
        await self.send_update(button="quote:back")
        self.assertIn(DATA["ru"]["pricing"]["choices"]["technical"]["text"],
                      self.edit_mock.call_args.kwargs["text"])
        await self.send_update(button="quote:pricing:technical")
        await self.send_update("Alex")
        await self.send_update(button="home")
        self.assertEqual(self.edit_mock.call_args.kwargs["text"], DATA["ru"]["messages"]["welcome"])
        self.assertEqual(self.app.user_data[123], {"language": "ru"})
        await self.send_update("unexpected text")
        self.assertEqual(self.send_mock.call_args.kwargs["text"], DATA["ru"]["messages"]["unknown"])

    async def test_selected_choice_reaches_administrator(self):
        await self.send_update("/start")
        await self.send_update(button="language:en")
        await self.send_update(button="process")
        await self.send_update(button="process:content")
        await self.send_update(button="quote:process:content")
        await self.send_update("Alex")
        await self.send_update("alex@example.com")
        await self.send_update("example.com")
        await self.send_update("Update pages monthly")
        admin = self.admin_calls()[-1].kwargs["text"]
        self.assertIn("Service: Content support", admin)
        self.assertIn("Website: example.com", admin)


    async def test_language_selector_can_return_home(self):
        await self.send_update("/start")
        language_buttons = self.send_mock.call_args.kwargs["reply_markup"].inline_keyboard
        self.assertEqual(language_buttons[-1][0].callback_data, "home")
        await self.send_update(button="home")
        self.assertEqual(self.edit_mock.call_args.kwargs["text"], DATA["en"]["messages"]["welcome"])
        await self.send_update(button="language:ru")
        await self.send_update("/language")
        await self.send_update(button="home")
        self.assertEqual(self.edit_mock.call_args.kwargs["text"], DATA["ru"]["messages"]["welcome"])

    async def test_start_resets_active_request(self):
        await self.send_update("/start")
        await self.send_update(button="language:en")
        await self.send_update(button="quote")
        await self.send_update("Alex")
        await self.send_update("/start")
        self.assertNotIn("quote_state", self.app.user_data[123])
        await self.send_update(button="language:ru")
        await self.send_update("unexpected text")
        self.assertEqual(self.send_mock.call_args.kwargs["text"], DATA["ru"]["messages"]["unknown"])


    async def test_repeated_button_does_not_raise(self):
        await self.send_update("/start")
        await self.send_update(button="language:en")
        self.edit_mock.side_effect = BadRequest("Message is not modified")
        await self.send_update(button="home")
        self.assertEqual(self.errors, [])


    async def test_repeated_language_button_does_not_raise(self):
        await self.send_update("/start")
        await self.send_update(button="language:ru")
        await self.send_update(button="language")
        self.assertEqual(self.markup_mock.call_args.kwargs["reply_markup"].inline_keyboard[-1][0].callback_data,
                         "home")
        self.markup_mock.side_effect = BadRequest("Message is not modified")
        await self.send_update(button="language")
        self.assertEqual(self.errors, [])
