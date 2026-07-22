import unittest
from unittest.mock import AsyncMock, patch

from app.services.message_handler import handle_incoming_message


class TestMessageHandler(unittest.IsolatedAsyncioTestCase):
    async def test_voice_message_decodes_base64_and_transcribes(self):
        payload = {
            "from": "236360740958277@lid",
            "type": "voice",
            "media": {
                "mimetype": "audio/ogg; codecs=opus",
                "data": "SGVsbG8sIHdvcmxkIQ=="  # base64 for "Hello, world!"
            }
        }

        with patch("app.services.message_handler.transcribe_audio", new=AsyncMock(return_value="hello world")) as mock_transcribe, \
             patch("app.services.message_handler.run_agent", new=AsyncMock(return_value="response text")) as mock_run_agent, \
             patch("app.services.message_handler.send_text_message", new=AsyncMock(return_value=True)) as mock_send_text:

            result = await handle_incoming_message(payload)

            self.assertEqual(result["status"], "success")
            mock_transcribe.assert_awaited_once()
            mock_run_agent.assert_awaited_once_with("hello world", payload["from"], result["trace_id"])
            mock_send_text.assert_awaited_once_with(payload["from"], "response text", result["trace_id"])


if __name__ == "__main__":
    unittest.main()
