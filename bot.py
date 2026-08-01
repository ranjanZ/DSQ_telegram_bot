import logging
import os
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes,
)
from config import BOT_TOKEN
from handlers.commands import handlers
from chat_agent.telegram_integration import get_natural_language_handler

# ==================== LOGGING SETUP ====================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# ==================== ERROR HANDLER ====================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error(msg="Exception while handling an update:", exc_info=context.error)

# ==================== MESSAGE LOGGING (to file) ====================
LOG_DIR = "data"
LOG_FILE = os.path.join(LOG_DIR, "chat_log.txt")
os.makedirs(LOG_DIR, exist_ok=True)

async def log_every_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log every single text message (including commands) to a file."""
    if update.message and update.message.text:
        user = update.effective_user
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {user.full_name} (@{user.username}) (id:{user.id}) → {update.message.text}"

        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

# ==================== MAIN ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # 🔁 Runs BEFORE every other handler (group=-1)
    app.add_handler(
        MessageHandler(filters.ALL, log_every_message), group=-1
    )

    # Your normal handlers (from commands.py) - group=0 by default
    for handler in handlers:
        app.add_handler(handler)

    # 🤖 Natural language handler (fallback, group=1)
    # This handles non-command messages using the LangGraph agent
    app.add_handler(get_natural_language_handler(), group=1)

    app.add_error_handler(error_handler)

    logging.info("🤖 Bot running with AI agent. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()