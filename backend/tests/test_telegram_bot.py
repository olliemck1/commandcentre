import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.config import settings
from app.database import SessionLocal
from app.models.journal import JournalEntry
from app.models.nutrition import NutritionLog
from app.models.crm import Person
from app.services.telegram_bot import (
    check_auth,
    is_query_message,
    clean_query_text,
    format_journal_summary,
    handle_text_message,
    handle_voice_message,
    start_command,
    help_command,
    query_command,
    status_command,
)

def create_mock_update(user_id=123456, text=None, voice=None, username="testuser"):
    update = MagicMock()
    update.effective_user.id = user_id
    update.effective_user.username = username
    
    if text is not None:
        message = MagicMock()
        message.text = text
        message.voice = None
        # Mock reply_text returning a message with an async edit_text
        ack_msg = MagicMock()
        ack_msg.edit_text = AsyncMock()
        message.reply_text = AsyncMock(return_value=ack_msg)
        update.message = message
    elif voice is not None:
        message = MagicMock()
        message.text = None
        message.voice = voice
        ack_msg = MagicMock()
        ack_msg.edit_text = AsyncMock()
        message.reply_text = AsyncMock(return_value=ack_msg)
        update.message = message
    else:
        message = MagicMock()
        message.text = None
        message.voice = None
        ack_msg = MagicMock()
        ack_msg.edit_text = AsyncMock()
        message.reply_text = AsyncMock(return_value=ack_msg)
        update.message = message

    return update


def test_auth_guard_rejection():
    """Verify unauthorized user IDs are rejected and no reply is sent."""
    with patch.object(settings, "ALLOWED_TELEGRAM_USER_ID", "123456"):
        # Unknown ID
        unauthorized_update = create_mock_update(user_id=999999, text="Today was great")
        assert check_auth(unauthorized_update) is False

        # Blank allowed configuration rejects everyone
        with patch.object(settings, "ALLOWED_TELEGRAM_USER_ID", ""):
            assert check_auth(unauthorized_update) is False


def test_auth_guard_allowed():
    """Verify authorized user IDs pass check_auth, including comma-separated lists."""
    with patch.object(settings, "ALLOWED_TELEGRAM_USER_ID", "123456"):
        authorized_update = create_mock_update(user_id=123456)
        assert check_auth(authorized_update) is True

    with patch.object(settings, "ALLOWED_TELEGRAM_USER_ID", "1001, 123456, 2002"):
        authorized_update = create_mock_update(user_id=123456)
        assert check_auth(authorized_update) is True


def test_is_query_detection():
    """Verify heuristic distinction between queries and daily logs."""
    assert is_query_message("What did I eat yesterday?") is True
    assert is_query_message("what is on my timetable today") is True
    assert is_query_message("How many calories have I consumed?") is True
    assert is_query_message("Who did I meet last week?") is True
    assert is_query_message("where is my next lecture?") is True
    assert is_query_message("/query upcoming assignments") is True
    assert is_query_message("/ask who is Alex") is True
    assert is_query_message("Did I take 10,000 steps today?") is True
    assert is_query_message("Can you show me my journal from Monday?") is True
    assert is_query_message("Summarize my sleep score") is True
    assert is_query_message("Are there any deadlines this week?") is True

    # Daily journals / activity logs should NOT be classified as queries
    assert is_query_message("Had an oat milk latte and eggs for breakfast. Productive morning coding.") is False
    assert is_query_message("Lunch with Marcus at Dishoom. Ate chicken and rice (650 cal).") is False
    assert is_query_message("Went for a 5km run this evening, felt great!") is False
    assert is_query_message("") is False


def test_clean_query_text():
    assert clean_query_text("/query what did I eat?") == "what did I eat?"
    assert clean_query_text("/ask how many steps?") == "how many steps?"
    assert clean_query_text("/q where is COMP2181?") == "where is COMP2181?"
    assert clean_query_text("What did I eat?") == "What did I eat?"


def test_format_journal_summary_payloads():
    """Verify response payload formatting functions without throwing uncaught exceptions."""
    # 1. Full payload with nutrition, people, tags
    full_entry = {
        "date": "2026-10-06",
        "mood": "Productive & Energetic",
        "summary": "Met Sarah for coffee and had lunch at Dishoom.",
        "nutrition": {
            "total_calories": 750,
            "total_protein_g": 38.0,
            "total_carbs_g": 62.0,
            "total_fat_g": 20.0,
            "items": [
                {"name": "Oat Milk Latte", "calories": 140},
                {"name": "Chicken Bowl", "calories": 610}
            ]
        },
        "people": [
            {
                "name": "Sarah",
                "sentiment": "positive",
                "context": "Coffee at Blue Bottle discussing launch",
                "facts_learned": ["Likes oat milk flat whites"],
                "location": "Blue Bottle"
            }
        ],
        "tags": ["coffee", "social", "nutrition"]
    }
    summary = format_journal_summary(full_entry)
    assert "2026-10-06" in summary
    assert "Productive & Energetic" in summary
    assert "750 kcal" in summary
    assert "Protein: 38.0g" in summary
    assert "Oat Milk Latte" in summary
    assert "Sarah" in summary
    assert "Blue Bottle" in summary
    assert "#coffee" in summary

    # 2. Minimal payload without nutrition and without people
    minimal_entry = {
        "date": "2026-10-06",
        "mood": "Calm & Grounded",
        "summary": "Read a book in the park.",
        "nutrition": {"total_calories": 0, "items": []},
        "people": [],
        "tags": ["reading"]
    }
    min_summary = format_journal_summary(minimal_entry)
    assert "Calm & Grounded" in min_summary
    assert "Read a book" in min_summary
    assert "Nutrition Logged" not in min_summary
    assert "People & CRM Updated" not in min_summary
    assert "#reading" in min_summary


@pytest.mark.anyio
async def test_unauthorized_user_message_ignored():
    """Ensure update from unauthorized user is completely ignored."""
    with patch.object(settings, "ALLOWED_TELEGRAM_USER_ID", "123456"):
        update = create_mock_update(user_id=888888, text="My private journal entry")
        context = MagicMock()

        await handle_text_message(update, context)
        # Verify no message sent or acknowledged
        update.message.reply_text.assert_not_called()


@pytest.mark.anyio
async def test_valid_text_triggers_journal_and_crm_extraction():
    """Ensure authorized text correctly triggers journal creation with source='telegram' and CRM updates."""
    with patch.object(settings, "ALLOWED_TELEGRAM_USER_ID", "123456"):
        text = "Met Marcus Vance for lunch at Dishoom. He is moving to Seattle. Ate chicken and rice (around 650 cal)."
        update = create_mock_update(user_id=123456, text=text)
        context = MagicMock()

        await handle_text_message(update, context)

        # 1. Acknowledged immediately
        update.message.reply_text.assert_called_once()
        ack_call_arg = update.message.reply_text.call_args[0][0]
        assert "Processing entry" in ack_call_arg

        # 2. Ack message was edited with the extracted summary
        ack_msg = await update.message.reply_text()
        ack_msg.edit_text.assert_called_once()
        summary_arg = ack_msg.edit_text.call_args[0][0]
        assert "Journal Entry Recorded" in summary_arg
        assert "Marcus" in summary_arg

        # 3. Verify SQLite DB has the entry with source='telegram'
        with SessionLocal() as db:
            entry = db.query(JournalEntry).filter(JournalEntry.raw_text == text).first()
            assert entry is not None
            assert entry.source == "telegram"
            assert entry.mood is not None

            # Verify nutrition was logged
            nut_logs = db.query(NutritionLog).filter(NutritionLog.journal_entry_id == entry.id).all()
            assert len(nut_logs) >= 1
            assert any("chicken" in nl.item_name.lower() or "meal" in nl.item_name.lower() for nl in nut_logs)

            # Verify CRM person was created/updated
            person = db.query(Person).filter(Person.name.like("%Marcus%")).first()
            assert person is not None


@pytest.mark.anyio
async def test_conversational_query_routing():
    """Ensure messages detected as queries are routed to chat_service retrieval tools."""
    with patch.object(settings, "ALLOWED_TELEGRAM_USER_ID", "123456"):
        update = create_mock_update(user_id=123456, text="What did I eat recently?")
        context = MagicMock()

        await handle_text_message(update, context)

        # 1. Acknowledged with query indicator
        update.message.reply_text.assert_called_once()
        ack_arg = update.message.reply_text.call_args[0][0]
        assert "Searching Command Centre" in ack_arg

        # 2. Answer provided in edit_text
        ack_msg = await update.message.reply_text()
        ack_msg.edit_text.assert_called_once()
        answer_arg = ack_msg.edit_text.call_args[0][0]
        assert len(answer_arg) > 10


@pytest.mark.anyio
async def test_explicit_query_command():
    """Ensure /query command works explicitly."""
    with patch.object(settings, "ALLOWED_TELEGRAM_USER_ID", "123456"):
        update = create_mock_update(user_id=123456)
        context = MagicMock()
        context.args = ["what", "are", "my", "upcoming", "deadlines"]

        await query_command(update, context)
        update.message.reply_text.assert_called_once()
        ack_msg = await update.message.reply_text()
        ack_msg.edit_text.assert_called_once()


@pytest.mark.anyio
async def test_help_and_start_commands():
    """Ensure /start and /help return guidance messages for authorized users."""
    with patch.object(settings, "ALLOWED_TELEGRAM_USER_ID", "123456"):
        update = create_mock_update(user_id=123456)
        context = MagicMock()

        await start_command(update, context)
        assert update.message.reply_text.call_count == 1
        start_reply = update.message.reply_text.call_args[0][0]
        assert "Welcome to Command Centre" in start_reply

        update.message.reply_text.reset_mock()
        await help_command(update, context)
        assert update.message.reply_text.call_count == 1
        help_reply = update.message.reply_text.call_args[0][0]
        assert "Guide" in help_reply


@pytest.mark.anyio
async def test_voice_note_transcription_and_ingestion():
    """Ensure voice note is downloaded, transcribed via LLM service, and ingested."""
    with patch.object(settings, "ALLOWED_TELEGRAM_USER_ID", "123456"):
        mock_voice = MagicMock()
        mock_file = MagicMock()
        mock_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"FAKE_OGG_BYTES"))
        mock_voice.get_file = AsyncMock(return_value=mock_file)

        update = create_mock_update(user_id=123456, voice=mock_voice)
        context = MagicMock()

        # Mock LLM audio transcription
        transcription = "Had a flat white with Sarah Vance and planned the marketing campaign."
        with patch("app.services.telegram_bot.llm_service.transcribe_audio", AsyncMock(return_value=transcription)):
            await handle_voice_message(update, context)

            # Check that download was requested
            mock_voice.get_file.assert_called_once()
            mock_file.download_as_bytearray.assert_called_once()

            # Check reply with Voice Note Logged
            assert update.message.reply_text.call_count >= 2
            final_call = update.message.reply_text.call_args_list[-1]
            assert "Voice Note Logged" in final_call[0][0]
            assert "Sarah" in final_call[0][0]
