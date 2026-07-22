import os
import httpx
from dotenv import load_dotenv
from app.logger import get_logger

load_dotenv()
logger = get_logger(__name__)

OPENWA_URL = os.getenv("OPENWA_URL", "http://localhost:2785")
OPENWA_API_KEY = os.getenv("OPENWA_API_KEY", "")
OPENWA_SESSION_ID = os.getenv("OPENWA_SESSION_ID")


async def send_text_message(phone_number: str, message: str, trace_id: str) -> bool:
    """
    Send text message back to WhatsApp user via OpenWA API.
    phone_number format: 447812345678 (without @c.us)
    """
    chat_id = phone_number
    url = f"{OPENWA_URL}/api/sessions/{OPENWA_SESSION_ID}/messages/send-text"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={
                    "X-API-Key": OPENWA_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "chatId": chat_id,
                    "text": message
                },
                timeout=15.0
            )

            if response.status_code in [200, 201]:
                logger.info(f"[{trace_id}] WhatsApp message sent | phone={phone_number[-4:]}")
                return True
            else:
                logger.error(f"[{trace_id}] WhatsApp send failed | status={response.status_code} | body={response.text[:100]}")
                return False

    except Exception as e:
        logger.error(f"[{trace_id}] WhatsApp send error | error={e}")
        return False


def extract_phone_number(chat_id: str) -> str:
    """Extract phone number from WhatsApp chat ID format: 447812345678@c.us"""
    return chat_id.replace("@c.us", "").replace("@g.us", "").replace("@lid", "")


def detect_message_type(payload: dict) -> str:
    """
    Detect message type from OpenWA webhook payload.
    Returns: 'voice', 'text', or 'unsupported'
    """
    msg_type = payload.get("type", "")
    if msg_type in ["audio", "ptt", "voice"]:  # ptt = push to talk (voice note)
        return "voice"
    elif msg_type == "text":
        return "text"
    return "unsupported"


def get_message_text(payload: dict) -> str:
    """Extract text content from webhook payload."""
    return payload.get("body", "") or payload.get("text", "") or ""


def get_media_url(payload: dict) -> str:
    """Extract media URL from webhook payload for voice messages."""
    media = payload.get("media", {}) or {}
    return media.get("url", "") or payload.get("mediaUrl", "")


def get_media_data(payload: dict) -> str:
    """Extract base64 audio data from webhook payload for voice messages."""
    media = payload.get("media", {}) or {}
    return media.get("data", "") or payload.get("mediaData", "")
