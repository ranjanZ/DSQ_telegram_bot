import logging
import os
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes,
    CommandHandler,
)
from config import BOT_TOKEN
from handlers.commands import handlers
from chat_agent.agent import run_agent, enter_agent_mode, exit_agent_mode, is_in_agent_mode

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

# ==================== AGENT MODE COMMAND ====================
async def agent_mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enter agent mode when user types /agent_mode"""
    user_id = str(update.effective_user.id)
    response = enter_agent_mode(user_id)
    await update.message.reply_text(response, parse_mode="Markdown")

# ==================== NATURAL LANGUAGE HANDLER ====================
async def natural_language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle natural language messages when in agent mode.
    This handler processes all text messages that are not commands.
    """
    if not update.message or not update.message.text:
        return
    
    # Skip if it's a command (commands start with /)
    if update.message.text.startswith('/'):
        return
    
    user_id = str(update.effective_user.id)
    
    # Check if user is in agent mode
    if not is_in_agent_mode(user_id):
        return  # Not in agent mode, let other handlers process or ignore
    
    # Process with the agent
    try:
        response = run_agent(update.message.text, user_id)
        await update.message.reply_text(response, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error in agent processing: {e}")
        await update.message.reply_text("Sorry, I encountered an error. Please try again or type 'exit' to leave agent mode.")

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
    
    # 🤖 Agent Mode Command - group=0 (same priority as other commands)
    app.add_handler(CommandHandler("agent_mode", agent_mode_command), group=0)

    # 💬 Natural language handler for agent mode - group=1 (fallback)
    # Only processes messages when user is in agent mode
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, natural_language_handler), 
        group=1
    )

    app.add_error_handler(error_handler)

    logging.info("🤖 Bot running with AI agent. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()