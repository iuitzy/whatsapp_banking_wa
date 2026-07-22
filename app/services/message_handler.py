from base64 import b64decode
import time
import uuid
from app.logger import get_logger
from app.metrics import (
    log_message_received,
    log_transcription,
    log_agent_call,
    log_whatsapp_send,
    log_request
)
from app.services.whatsapp import (
    extract_phone_number,
    detect_message_type,
    get_message_text,
    get_media_url,
    get_media_data,
    send_text_message
)
from app.services.transcription import download_audio, transcribe_audio
from app.agent.agent import run_agent
import os

logger = get_logger(__name__)

OPENWA_API_KEY = os.getenv("OPENWA_API_KEY", "")


async def handle_incoming_message(payload: dict) -> dict:
    """
    Main handler for incoming WhatsApp messages.

    Flow:
    1. Generate trace ID
    2. Extract phone number and message type
    3. If voice — download and transcribe
    4. If text — use directly
    5. Run LangGraph agent
    6. Send response back to WhatsApp
    7. Log everything with trace ID
    """
    request_start = time.time()
    trace_id = str(uuid.uuid4())[:8]

    try:
        # Extract sender info
        sender = payload.get("from", "") or payload.get("sender", "")
        phone_number = extract_phone_number(sender)
        logger.info(f"[{trace_id}] Extracted phone number: {phone_number}")

        # # Extract to person info
        # to_person = payload.get("to", "")
        # logger.info(f"[{trace_id}] Extracted to person: {to_person}")

        # Extract from person info
        from_person = payload.get("from", "")
        logger.info(f"[{trace_id}] Extracted from person: {from_person}")

        if not phone_number:
            logger.warning(f"[{trace_id}] No phone number in payload")
            return {"status": "error", "message": "No sender found"}

        # Detect message type
        logger.info(f"[{trace_id}] Payload for type detection: type={payload.get('type')}, body={payload.get('body')}, media_present={bool(payload.get('media'))}")
        msg_type = detect_message_type(payload)
        logger.info(f"[{trace_id}] Detected message type: {msg_type}")
        log_message_received(phone_number, msg_type, trace_id)

        logger.info(f"[{trace_id}] Message received | phone={phone_number[-4:]} | type={msg_type}")

        # Handle based on type
        query = ""

        if msg_type == "text":
            query = get_message_text(payload)
            logger.info(f"[{trace_id}] Text message | content={query[:50]}")

        elif msg_type == "voice":
            logger.info(f"[{trace_id}] Voice message — transcribing")
            media_url = get_media_url(payload)
            media_data_base64 = ""
            if not media_url:
                media_data_base64 = get_media_data(payload)

            raw_media = payload.get("media")
            raw_media_desc = None
            if isinstance(raw_media, dict):
                raw_media_desc = {k: (v[:50] + "..." if isinstance(v, str) and len(v) > 50 else v) for k, v in raw_media.items()}
            else:
                raw_media_desc = raw_media

            logger.info(
                f"[{trace_id}] Extracted media | media_present={bool(raw_media)} | media_type={type(raw_media).__name__} | media_keys={list(raw_media.keys()) if isinstance(raw_media, dict) else None} | media_raw={raw_media_desc} | media_url_prefix={repr(str(media_url)[:50])}"
            )

            audio_data = None
            if media_url:
                audio_data = await download_audio(media_url, OPENWA_API_KEY, trace_id)
            elif media_data_base64:
                try:
                    audio_data = b64decode(media_data_base64)
                    logger.info(f"[{trace_id}] Decoded base64 voice media | bytes={len(audio_data)}")
                except Exception as exc:
                    logger.error(f"[{trace_id}] Failed to decode base64 voice media | error={exc}")

            if not audio_data:
                logger.error(f"[{trace_id}] No media URL or raw audio data in voice message")
                await send_text_message(
                    from_person,
                    "Sorry, I couldn't process your voice message. Please try sending a text message.",
                    trace_id
                )
                return {"status": "error", "trace_id": trace_id}

            # Transcribe with Groq Whisper
            transcribe_start = time.time()
            query = await transcribe_audio(audio_data, trace_id)
            transcribe_duration = (time.time() - transcribe_start) * 1000

            if not query:
                log_transcription(False, transcribe_duration, trace_id)
                await send_text_message(
                    from_person,
                    "Sorry, I couldn't understand your voice message. Please try again or send a text message.",
                    trace_id
                )
                return {"status": "error", "trace_id": trace_id}

            log_transcription(True, transcribe_duration, trace_id)
            logger.info(f"[{trace_id}] Transcribed: {query[:50]}")

        else:
            logger.info(f"[{trace_id}] Unsupported message type: {msg_type}")
            await send_text_message(
                from_person,
                "Sorry, I can only process text and voice messages. Please send a text or voice note.",
                trace_id
            )
            return {"status": "unsupported", "trace_id": trace_id}

        if not query or not query.strip():
            await send_text_message(
                from_person,
                "Sorry, I received an empty message. Please try again.",
                trace_id
            )
            return {"status": "error", "trace_id": trace_id}

        # Run LangGraph agent
        agent_start = time.time()
        response = await run_agent(query, sender, trace_id)
        agent_duration = (time.time() - agent_start) * 1000
        log_agent_call(True, agent_duration, [], trace_id)

        # Send response back to WhatsApp
        send_success = await send_text_message(from_person, response, trace_id)
        log_whatsapp_send(send_success, trace_id)

        # Log total request time
        total_duration = (time.time() - request_start) * 1000
        log_request(total_duration, trace_id)

        logger.info(f"[{trace_id}] Request complete | total={total_duration:.2f}ms")

        return {
            "status": "success",
            "trace_id": trace_id,
            "phone": phone_number[-4:],
            "type": msg_type,
            "duration_ms": round(total_duration, 2)
        }

    except Exception as e:
        total_duration = (time.time() - request_start) * 1000
        logger.error(f"[{trace_id}] Request failed | error={e} | duration={total_duration:.2f}ms")
        return {"status": "error", "trace_id": trace_id, "error": str(e)}
