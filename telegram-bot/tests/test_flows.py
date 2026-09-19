"""User journeys through the real Telegram update router, without network access."""

import asyncio
import os
import unittest
import warnings
from unittest.mock import AsyncMock, patch

from telegram import Update, User

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
        self.answer = patch.object(self.bot_type, "answer_callback_query", new_callable=AsyncMock)
        bot_user = User(id=123456, is_bot=True, first_name="Test Bot", username="test_bot")
        self.get_me.start().return_value = bot_user
        self.send_mock = self.send.start()
        self.edit_mock = self.edit.start()
        self.answer_mock = self.answer.start()
        await self.app.initialize()
        self.app.bot._bot_user = bot_user
        self.errors = []
        self.app.add_error_handler(self.record_error)
        self.number = 0

    async def asyncTearDown(self):
        await self.app.shutdown()
        self.answer.stop()
        self.edit.stop()
        self.send.stop()
        self.get_me.stop()
        self.token.stop()

    async def record_error(self, update, context):
        self.errors.append(context.error)

    async def send_update(self, text=None, button=None):
        self.number += 1
        user = {"id": 123, "is_bot": False, "first_name": "Alex", "username": "alex"}
        message = {
            "message_id": self.number,
            "date": 1700000000,
            "chat": {"id": 123, "type": "private"},
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
                self.assertEqual(self.app.user_data[123], {"language": language})

    async def test_back_then_cancel_in_each_language(self):
        for language in ("en", "ru"):
            with self.subTest(language=language):
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
                self.assertEqual(self.app.user_data[123], {"language": language})
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
