"""Telegram Bot Service Entrypoint for Command Centre.
Run directly with: python services/telegram_bot.py
"""
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.services.telegram_bot import (
    run_bot,
    create_telegram_application,
    check_auth,
    is_query_message,
    format_journal_summary,
    handle_text_message,
    handle_voice_message,
    start_command,
    help_command,
    query_command,
    status_command,
)

if __name__ == "__main__":
    run_bot()
