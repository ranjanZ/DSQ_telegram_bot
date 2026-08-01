"""
Telegram Bot Integration with DSQ Chat Agent

This module integrates the LangGraph-based chat agent with the Telegram bot.
When a user sends a message that is NOT a command, the agent handles it.
"""

import logging
from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes
from chat_agent.agent import DSQChatAgent

logger = logging.getLogger(__name__)

# Initialize the chat agent
chat_agent = DSQChatAgent()


async def handle_natural_language_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle non-command messages using the chat agent.
    
    This handler processes natural language queries like:
    - "I want to get a license for dsq v2"
    - "How do I set up the bot?"
    - "What are the risks with v3?"
    - "My MT5 ID is 12345678, name is John"
    
    The agent maintains conversation context per user for multi-turn conversations.
    """
    if not update.message or not update.message.text:
        return
    
    # Get user's message and ID
    user_message = update.message.text
    user_id = str(update.effective_user.id)
    
    logger.info(f"Processing natural language message from user {user_id}: {user_message}")
    
    try:
        # Process with chat agent (uses conversation history)
        response = chat_agent.chat(user_message, user_id=user_id)
        
        # Send response back to user
        await update.message.reply_text(response, parse_mode="HTML")
        
        logger.info(f"Agent response sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error processing message with agent: {e}", exc_info=True)
        # Fallback response
        await update.message.reply_text(
            "I'm having trouble processing your request right now. "
            "Please try using one of the commands like /start, /get_licence_v2, etc."
        )


def get_natural_language_handler() -> MessageHandler:
    """
    Create and return the message handler for natural language messages.
    
    This handler:
    - Only processes text messages (not commands)
    - Has lower priority than command handlers (group=1)
    - Falls back to agent when no command matches
    """
    return MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_natural_language_message
    )


# Example usage in bot.py:
# 
# from chat_agent.telegram_integration import get_natural_language_handler
# 
# def main():
#     app = Application.builder().token(BOT_TOKEN).build()
#     
#     # Add command handlers first (higher priority, group=0 by default)
#     for handler in handlers:
#         app.add_handler(handler)
#     
#     # Add natural language handler (lower priority, group=1)
#     app.add_handler(get_natural_language_handler(), group=1)
#     
#     app.run_polling()
#
# How it works:
# 1. User sends: "I want to get a license for dsq v2"
#    → Agent responds asking for MT5 ID, Name, Broker, Account Type
# 2. User sends: "My MT5 ID is 12345678"
#    → Agent remembers and asks for remaining info
# 3. User sends: "Name is John, Broker XM, Real account"
#    → Agent provides complete response with /get_licence_v2 command
#
# The agent maintains conversation context per user, enabling natural multi-turn conversations.
