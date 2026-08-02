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
        logging.info(f"User {user_id} sent message but not in agent mode")
        return  # Not in agent mode, let other handlers process or ignore
    
    logging.info(f"Processing agent mode message from user {user_id}: {update.message.text}")
    
    # Process with the agent
    try:
        response = run_agent(update.message.text, user_id)
        logging.info(f"Agent response generated for user {user_id}")
        await update.message.reply_text(response, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error in agent processing: {e}", exc_info=True)
        # Check if it's a connection error (Ollama not running)
        if "Connection refused" in str(e) or "ConnectError" in str(type(e).__name__) or "HTTPStatusError" in str(type(e).__name__):
            await update.message.reply_text(
                "⚠️ *Agent Mode Error*\n\n"
                "The AI assistant requires Ollama to be running.\n\n"
                "Please start Ollama with:\n"
                "`ollama serve`\n\n"
                "Then pull the model if needed:\n"
                "`ollama pull llama3`\n\n"
                "Or type 'exit' to leave agent mode and use standard commands."
            )
        else:
            await update.message.reply_text(
                f"Sorry, I encountered an error: {str(e)}\n\n"
                "Please try again or type 'exit' to leave agent mode."
            )

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