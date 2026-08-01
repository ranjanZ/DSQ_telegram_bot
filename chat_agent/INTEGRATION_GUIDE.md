# Chat Agent Integration Guide

## Overview

This guide explains how to integrate the LangGraph-based chat agent with your Telegram bot to handle natural language queries.

## Two Approaches for Integration

### Approach 1: Fallback Handler (Recommended) ✅

**How it works:**
- Command handlers have priority (group=0)
- Natural language handler acts as fallback (group=1)
- If a message is NOT a command, the agent processes it

**Implementation:**

```python
# In bot.py
from chat_agent.telegram_integration import get_natural_language_handler

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Log all messages (group=-1, highest priority)
    app.add_handler(MessageHandler(filters.ALL, log_every_message), group=-1)

    # Command handlers (group=0, default)
    for handler in handlers:
        app.add_handler(handler)

    # Natural language handler (group=1, lower priority)
    app.add_handler(get_natural_language_handler(), group=1)

    app.run_polling()
```

**Pros:**
- ✅ Commands still work as before
- ✅ Natural language queries are automatically handled
- ✅ No changes needed to existing command handlers
- ✅ Clean separation of concerns

**Cons:**
- ⚠️ Need to ensure proper handler priority

---

### Approach 2: Explicit Agent Call in Start Command

**How it works:**
- Modify `/start` to inform users they can use natural language
- Optionally add a dedicated `/ask` command

**Implementation:**

```python
# In commands.py - modify start function
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "👋 Welcome! [Everything is free for now]\n\n"
        "You can use commands OR just talk to me naturally!\n\n"
        "Examples:\n"
        "• \"I want a license for dsq v2\"\n"
        "• \"How do I set up the bot?\"\n"
        "• \"What are the risks?\"\n\n"
        "/start – This menu\n"
        # ... rest of commands
    )
    await update.message.reply_text(msg, parse_mode="HTML")
```

---

## How the Agent Handles Conversations

### Multi-Turn Conversation Example

**Turn 1:**
```
User: "I want to get a license for dsq v2"
Agent: "To create a license for DSQ V2, I need:
        - MT5 ID
        - Name
        - Broker
        - Account Type (Demo/Real)
        
        Please provide these details."
```

**Turn 2:**
```
User: "My MT5 ID is 12345678"
Agent: "Got your MT5 ID: 12345678
        Still need: Name, Broker, Account Type"
```

**Turn 3:**
```
User: "Name is John Doe, using XM broker, Real account"
Agent: "Great! I have all information:
        - MT5 ID: 12345678
        - Name: John Doe
        - Broker: XM
        - Account Type: Real
        
        Use /get_licence_v2 to complete..."
```

### Key Features

1. **Context Persistence**: Agent remembers previous messages per user
2. **Entity Merging**: New information merges with existing context
3. **Follow-up Detection**: Automatically asks for missing info
4. **Intent Recognition**: Understands what user wants even if incomplete

---

## Implementation Details

### File Structure

```
chat_agent/
├── agent.py                 # Main LangGraph agent
├── telegram_integration.py  # Telegram handler
├── requirements.txt         # Dependencies
└── README.md               # Documentation
```

### Key Components

#### 1. DSQChatAgent Class (agent.py)

```python
class DSQChatAgent:
    def __init__(self):
        self.graph = create_agent_graph()
        self.conversation_states = {}  # Per-user conversation history
    
    def chat(self, user_query: str, user_id: str) -> str:
        # Maintains conversation context
        # Returns appropriate response
```

#### 2. Telegram Handler (telegram_integration.py)

```python
async def handle_natural_language_message(update, context):
    user_message = update.message.text
    user_id = str(update.effective_user.id)
    
    response = chat_agent.chat(user_message, user_id=user_id)
    await update.message.reply_text(response)
```

---

## Testing

### Test Multi-Turn Conversation

```bash
cd chat_agent
python agent.py
```

This runs a demo showing:
1. Multi-turn conversation with follow-ups
2. Single-turn with complete information

### Test with Telegram Bot

1. Start your bot
2. Send: "I want a license for dsq v2"
3. Agent should ask for missing info
4. Provide partial info
5. Agent should remember and ask for remaining
6. Provide rest of info
7. Agent should give complete response

---

## Configuration

### Change Ollama Model

Edit `chat_agent/agent.py`:

```python
llm = ChatOllama(
    model="llama3.2",      # Change model here
    base_url="http://localhost:11434",
    temperature=0.7
)
```

### Adjust Temperature

- Lower (0.3-0.5): More focused, deterministic
- Higher (0.7-0.9): More creative, varied responses

---

## Troubleshooting

### Issue: Agent not responding

**Solution:**
1. Check Ollama is running: `ollama serve`
2. Verify model exists: `ollama list`
3. Check imports in telegram_integration.py

### Issue: Conversation not persisting

**Solution:**
- Ensure same `user_id` is passed to `agent.chat()`
- Don't call `reset_conversation()` between turns

### Issue: Wrong intent detected

**Solution:**
- Improve prompt in `classify_intent()` function
- Add more examples to the prompt
- Consider fine-tuning with specific DSQ examples

---

## Best Practices

1. **Always use user_id**: Pass Telegram user ID for context persistence
2. **Handle errors gracefully**: Fallback to command suggestions
3. **Log conversations**: For debugging and improvement
4. **Test thoroughly**: Both single and multi-turn scenarios
5. **Monitor performance**: Ollama response times can vary

---

## Next Steps

After integration:

1. **Monitor Usage**: Track how often users use natural language vs commands
2. **Gather Feedback**: Ask users about their experience
3. **Improve Prompts**: Refine based on common queries
4. **Add Languages**: Support Hindi and other languages
5. **Enhance Capabilities**: Direct license creation, etc.

---

## Support

For issues or questions:
1. Check README.md in chat_agent folder
2. Review example code in agent.py
3. Test with `python agent.py` first
4. Check logs for error messages
