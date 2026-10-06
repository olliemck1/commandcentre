import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Ensure backend root is on sys.path for standalone process execution
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
import telegram.error

from app.config import settings
from app.database import SessionLocal
from app.routes.journal import process_and_save_journal_entry
from app.services.chat_service import chat_service
from app.services.llm_service import llm_service

logger = logging.getLogger("telegram_bot")

QUERY_STARTERS = (
    "what", "how", "who", "when", "where", "why", "which",
    "tell me", "show me", "give me", "find", "search", "summarize",
    "explain", "list", "check",
    "can you", "could you", "would you", "will you",
    "did i", "have i", "do i", "is there", "are there"
)

def check_auth(update: Update) -> bool:
    """Authentication Guard: Verify incoming update.effective_user.id against
    ALLOWED_TELEGRAM_USER_ID environment variable; ignore all messages from unknown IDs."""
    if not update.effective_user:
        return False

    user_id = str(update.effective_user.id)
    allowed_config = str(settings.ALLOWED_TELEGRAM_USER_ID or "").strip()
    if not allowed_config:
        logger.warning(
            f"Blocked access from user_id={user_id} (@{update.effective_user.username}): "
            f"ALLOWED_TELEGRAM_USER_ID is not configured."
        )
        return False

    allowed_ids = {aid.strip() for aid in allowed_config.split(",") if aid.strip()}
    if user_id not in allowed_ids:
        logger.warning(
            f"Unauthorized Telegram access attempt rejected: user_id={user_id} (@{update.effective_user.username})."
        )
        return False

    return True

def is_query_message(text: str) -> bool:
    """Detect if a message is a query rather than a daily journal log."""
    stripped = text.strip()
    if not stripped:
        return False

    if stripped.startswith(("/query", "/ask", "/q")):
        return True

    if stripped.endswith("?"):
        return True

    lower = stripped.lower()
    for starter in QUERY_STARTERS:
        if lower.startswith(starter + " ") or lower == starter:
            return True

    return False

def clean_query_text(text: str) -> str:
    """Strips command prefixes if present."""
    stripped = text.strip()
    for prefix in ("/query", "/ask", "/q"):
        if stripped.lower().startswith(prefix):
            return stripped[len(prefix):].strip()
    return stripped

def format_journal_summary(entry: Dict[str, Any]) -> str:
    """Formats the extracted journal intelligence into a clean Telegram summary:
    - Estimated calories and macro breakdown (if food was logged).
    - Mentioned people tagged and profiles updated.
    - Quick sentiment/mood confirmation."""
    date_str = entry.get("date", datetime.now().strftime("%Y-%m-%d"))
    mood = entry.get("mood", "Neutral")
    summary = entry.get("summary", "")
    nutrition = entry.get("nutrition") or {}
    people = entry.get("people") or []
    tags = entry.get("tags") or []

    lines = [
        f"✅ *Journal Entry Recorded* (`{date_str}`)",
        f"🎭 *Mood / Sentiment:* {mood}",
    ]

    if summary:
        lines.append(f"📝 *Summary:* {summary}")

    # 1. Nutrition breakdown (if food was logged)
    total_cals = nutrition.get("total_calories", 0)
    nut_items = nutrition.get("items") or []
    if total_cals > 0 or nut_items:
        p = nutrition.get("total_protein_g", 0)
        c = nutrition.get("total_carbs_g", 0)
        f = nutrition.get("total_fat_g", 0)
        lines.append("")
        lines.append(f"🥗 *Nutrition Logged:*")
        lines.append(f"• *Total Energy:* {total_cals:,} kcal")
        lines.append(f"• *Macros:* Protein: {p}g | Carbs: {c}g | Fat: {f}g")
        if nut_items:
            item_descriptions = []
            for it in nut_items:
                name = it.get("name", "Food")
                cal = it.get("calories", 0)
                item_descriptions.append(f"{name} ({cal} cal)")
            lines.append(f"• *Items:* {', '.join(item_descriptions)}")

    # 2. People tagged & CRM updates
    if people:
        lines.append("")
        lines.append("👥 *Mentioned People & CRM Updated:*")
        for p in people:
            name = p.get("name", "Contact")
            sentiment = p.get("sentiment", "neutral").capitalize()
            lines.append(f"• *{name}* ({sentiment})")
            if p.get("context"):
                lines.append(f"  - Context: _{p['context']}_")
            facts = p.get("facts_learned") or []
            if facts:
                lines.append(f"  - Facts: {', '.join(facts)}")
            if p.get("location"):
                lines.append(f"  - Location: {p['location']}")

    # 3. Tags
    if tags:
        tag_line = " ".join([f"#{t.replace(' ', '_')}" for t in tags])
        lines.append("")
        lines.append(f"🏷️ {tag_line}")

    return "\n".join(lines)

async def reply_safely(message, text: str, parse_mode: str = "Markdown"):
    """Sends reply with markdown, falling back to plain text if formatting parsing fails."""
    try:
        return await message.reply_text(text, parse_mode=parse_mode)
    except telegram.error.BadRequest as e:
        logger.warning(f"Markdown parse error: {e}. Falling back to plain text.")
        return await message.reply_text(text)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command."""
    if not check_auth(update):
        return

    welcome_text = (
        "🚀 *Welcome to Command Centre Telegram Bot*\n\n"
        "Your life telemetry and personal operating system assistant is active.\n\n"
        "✨ *Capabilities:*\n"
        "• *Journal Ingestion:* Send your day's log as text or voice notes. I will extract nutrition, macros, CRM contacts, and moods.\n"
        "• *Conversational Assistant:* Ask questions starting with *What*, *How*, *Who*, etc., or use `/query <question>`.\n"
        "• *Commands:*\n"
        "  - `/help`: Detailed usage guide\n"
        "  - `/query <text>`: Direct query to retrieval tools\n"
        "  - `/status`: Telemetry and sync status"
    )
    await reply_safely(update.message, welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /help command."""
    if not check_auth(update):
        return

    help_text = (
        "📖 *Command Centre Bot Guide*\n\n"
        "1. *Logging Journals & Nutrition:*\n"
        "Just send a text message describing what you did and ate:\n"
        "_\"Had an oat milk latte and porridge for breakfast. Met Sarah at Blue Bottle to discuss the redesign. Stressed day.\"_\n\n"
        "2. *Querying Life & University Data:*\n"
        "Ask natural questions:\n"
        "• _\"What did I eat yesterday?\"_\n"
        "• _\"When was the last time I saw Alex?\"_\n"
        "• _\"What assignments are due in the next 14 days?\"_\n"
        "• _\"How many steps did I take today?\"_\n\n"
        "3. *Voice Notes:*\n"
        "Send an audio voice note anytime; it will be transcribed and processed into your journal."
    )
    await reply_safely(update.message, help_text)

async def query_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /query and /ask commands."""
    if not check_auth(update):
        return

    query_text = " ".join(context.args) if context.args else ""
    if not query_text.strip():
        await reply_safely(update.message, "Please provide a query after the command, e.g. `/query what did I eat today?`")
        return

    await execute_query_pipeline(update, query_text)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /status command."""
    if not check_auth(update):
        return

    today_str = datetime.now().strftime("%Y-%m-%d")
    with SessionLocal() as db:
        res = await chat_service.process_chat(f"Summarize my steps and metrics for today", [], db)
        answer = res.get("answer", "System online.")

    status_text = (
        f"🟢 *Command Centre Status* (`{today_str}`)\n\n"
        f"• *Telegram Daemon:* Active & Long-polling\n"
        f"• *Authentication:* Verified (`user_id={update.effective_user.id}`)\n\n"
        f"{answer}"
    )
    await reply_safely(update.message, status_text)

async def execute_query_pipeline(update: Update, query_text: str):
    """Processes a conversational query through retrieval tools and responds."""
    ack_msg = await reply_safely(update.message, "🔍 Searching Command Centre...")
    try:
        with SessionLocal() as db:
            result = await chat_service.process_chat(query_text, [], db)
            answer = result.get("answer", "No answer found.")

        try:
            await ack_msg.edit_text(answer, parse_mode="Markdown")
        except telegram.error.BadRequest:
            await ack_msg.edit_text(answer)
    except Exception as e:
        logger.error(f"Error handling query: {e}", exc_info=True)
        await ack_msg.edit_text(f"❌ Error processing query: {str(e)}")

async def execute_journal_pipeline(update: Update, text: str):
    """Processes raw journal text through extraction pipeline and replies with summary."""
    ack_msg = await reply_safely(update.message, "⏳ Processing entry...")
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        with SessionLocal() as db:
            result = await process_and_save_journal_entry(
                db=db,
                raw_text=text,
                date_str=today_str,
                source="telegram"
            )

        summary_text = format_journal_summary(result)
        try:
            await ack_msg.edit_text(summary_text, parse_mode="Markdown")
        except telegram.error.BadRequest:
            await ack_msg.edit_text(summary_text)
    except Exception as e:
        logger.error(f"Error handling journal ingestion: {e}", exc_info=True)
        await ack_msg.edit_text(f"❌ Error saving journal entry: {str(e)}")

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dispatches text messages to either query handling or journal ingestion."""
    if not check_auth(update):
        return

    text = update.message.text or ""
    if not text.strip():
        return

    if is_query_message(text):
        cleaned_query = clean_query_text(text)
        await execute_query_pipeline(update, cleaned_query)
    else:
        await execute_journal_pipeline(update, text)

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming voice notes: downloads audio, transcribes, and runs pipeline."""
    if not check_auth(update):
        return

    if not update.message.voice:
        return

    ack_msg = await reply_safely(update.message, "🎙️ Downloading voice note and transcribing...")
    try:
        voice_file = await update.message.voice.get_file()
        audio_bytes = await voice_file.download_as_bytearray()

        transcribed_text = await llm_service.transcribe_audio(
            audio_bytes=bytes(audio_bytes),
            filename="voice_note.ogg",
            mime_type="audio/ogg"
        )

        if not transcribed_text or not transcribed_text.strip():
            await ack_msg.edit_text("❌ Could not transcribe audio. Ensure an LLM API key (Gemini or OpenAI) is configured.")
            return

        # Let user know what was heard
        await ack_msg.edit_text(f"🎙️ *Transcribed:* \"_{transcribed_text}_\"\n\n⏳ Processing...")

        if is_query_message(transcribed_text):
            cleaned = clean_query_text(transcribed_text)
            with SessionLocal() as db:
                result = await chat_service.process_chat(cleaned, [], db)
                answer = result.get("answer", "No answer found.")
            response_msg = f"🎙️ *Voice Query:* \"{transcribed_text}\"\n\n{answer}"
            await reply_safely(update.message, response_msg)
        else:
            today_str = datetime.now().strftime("%Y-%m-%d")
            with SessionLocal() as db:
                entry = await process_and_save_journal_entry(
                    db=db,
                    raw_text=transcribed_text,
                    date_str=today_str,
                    source="telegram"
                )
            summary = format_journal_summary(entry)
            await reply_safely(update.message, f"🎙️ *Voice Note Logged:*\n\n{summary}")

    except Exception as e:
        logger.error(f"Error handling voice message: {e}", exc_info=True)
        await ack_msg.edit_text(f"❌ Error handling voice note: {str(e)}")

def create_telegram_application():
    """Builds and configures the telegram bot application."""
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not configured in settings or environment.")

    app = ApplicationBuilder().token(token).build()

    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("query", query_command))
    app.add_handler(CommandHandler("ask", query_command))
    app.add_handler(CommandHandler("status", status_command))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))

    return app

def run_bot():
    """Starts the Telegram bot service with long polling."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logger.info("Initializing Telegram bot service...")
    try:
        app = create_telegram_application()
    except ValueError as e:
        logger.error(f"Cannot start Telegram bot: {e}")
        return

    allowed = settings.ALLOWED_TELEGRAM_USER_ID or "(none - ALL BLOCKED)"
    logger.info(f"Telegram bot initialized. Allowed user IDs: {allowed}")
    logger.info("Starting long polling daemon...")
    app.run_polling()

if __name__ == "__main__":
    run_bot()
