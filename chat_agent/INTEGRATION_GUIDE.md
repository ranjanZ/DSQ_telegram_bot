# DSQ Chat Agent - Telegram Integration Guide

## ✅ Integration Complete!

The LangGraph-based chat agent has been successfully integrated into your Telegram bot using **Approach 1: Fallback Handler**.

## How It Works

### Handler Priority System

The bot now uses a priority-based handler system:

```
Group -1: Message logging (runs first, logs ALL messages)
Group  0: Command handlers (/start, /get_licence_v2, etc.)
Group  1: Natural language agent (fallback for non-command messages)
```

### Flow Diagram

```
User sends message
    ↓
Is it a command? (starts with /)
    ├─ YES → Command handler processes it (group=0)
    └─ NO  → Agent processes it (group=1)
                ↓
        Agent classifies intent
                ↓
        Extracts entities (MT5 ID, name, broker, account type)
                ↓
        Has all info? 
            ├─ NO  → Asks follow-up question
            └─ YES → Provides complete response
```

## What's Been Added

### 1. Updated `bot.py`

```python
from chat_agent.telegram_integration import get_natural_language_handler

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Message logging (group=-1)
    app.add_handler(MessageHandler(filters.ALL, log_every_message), group=-1)
    
    # Command handlers (group=0 by default)
    for handler in handlers:
        app.add_handler(handler)
    
    # 🆕 Natural language handler (group=1) - FALLBACK APPROACH
    app.add_handler(get_natural_language_handler(), group=1)
    
    app.run_polling()
```

### 2. Created `chat_agent/telegram_integration.py`

This module:
- Handles non-command text messages
- Maintains conversation context per user
- Routes queries to the LangGraph agent
- Provides fallback error handling

### 3. Enhanced `chat_agent/agent.py`

The agent now supports:
- **Multi-turn conversations** - Remembers context across messages
- **Automatic follow-up questions** - Asks for missing information
- **Entity merging** - Combines info from multiple messages
- **Intent classification** - Understands what user wants
- **4 bot versions** - V1, V2, V3, V4 support

## Usage Examples

### Example 1: Getting a License (Multi-turn)

```
User: I want to get a license for dsq v2

Agent: To create a license for DSQ V2, I need the following information:
- MT5 ID
- Name
- Broker
- Account Type (Demo/Real)

Please provide these details. You can give me all at once or one at a time.

Partner codes to add before creating license:
• Vantage: VcM6U1DW
• Roboforex: zrfhm
• XM: 4299V
• Exness: c_niibgmkreg

User: My MT5 ID is 12345678

Agent: [Remembers MT5 ID, still needs Name, Broker, Account Type]
Great! I have your MT5 ID. I still need:
- Name
- Broker
- Account Type (Demo/Real)

User: Name is John, Broker XM, Real account

Agent: Great! I have all the information needed for your DSQ V2 license:
- MT5 ID: 12345678
- Name: John
- Broker: XM
- Account Type: Real

To complete the license creation, please use:
/get_licence_v2
```

### Example 2: Setup Help

```
User: How do I set up the bot?

Agent: 🛠️ DSQ V1 Setup Guide:
1. Download & Login to MT5...
[Complete setup instructions]
```

### Example 3: Risk Information

```
User: What are the risks with v3?

Agent: ⚠️ DSQ V3 Risk Information:
For traders with ~10,000 INR...
[Risk details]
```

### Example 4: Download Request

```
User: I need to download dsq v4

Agent: 📦 Download DSQ V4:
Direct download link:
https://github.com/ranjanZ/DSQ_Page/raw/refs/heads/main/data/bots/dsq_v4.ex5

Or use: /get_dsq_v4
```

## Conversation Context Features

### Automatic Context Persistence

The agent automatically:
- Stores conversation state per user ID
- Remembers extracted entities across messages
- Merges new information with previous context
- Detects when user is providing follow-up answers

### Context Example

```
Message 1: "I want license for v2"
→ Agent stores: {bot_version: "v2", current_task: "license_creation"}

Message 2: "MT5 ID is 12345678"
→ Agent updates: {mt5_id: "12345678"}

Message 3: "Name is John"
→ Agent updates: {name: "John"}

Message 4: "XM broker, demo account"
→ Agent updates: {broker: "XM", account_type: "Demo"}
→ Now has all info → Provides complete response
```

## Installation Requirements

Make sure you have the required dependencies:

```bash
pip install langgraph langchain-ollama ollama python-telegram-bot
```

Or install from requirements:

```bash
pip install -r chat_agent/requirements.txt
```

## Ollama Setup

The agent uses Ollama with llama3.2 model. Make sure Ollama is running:

```bash
# Install Ollama (if not installed)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull the model
ollama pull llama3.2

# Start Ollama server
ollama serve
```

## Testing the Integration

1. Start your bot:
```bash
python bot.py
```

2. Send a non-command message in Telegram:
```
"I want to get a license for dsq v2"
```

3. The agent should respond asking for missing information.

4. Provide the information in one or multiple messages.

5. The agent will guide you to use the appropriate command.

## Customization Options

### Change the Model

Edit `chat_agent/agent.py`:

```python
llm = ChatOllama(
    model="llama3.2",  # Change to any Ollama model
    base_url="http://localhost:11434",
    temperature=0.7
)
```

Available models: `llama3.2`, `mistral`, `gemma2`, `phi3`, etc.

### Adjust Follow-up Behavior

Modify the `handle_license_request` function in `agent.py` to customize:
- Required fields
- Response format
- Partner codes displayed

### Add New Intents

1. Add new intent classification in `classify_intent`
2. Create new handler function
3. Update `route_by_intent` function
4. Add edge in graph creation

## Troubleshooting

### Agent Not Responding

1. Check if Ollama is running: `ollama list`
2. Verify model is available: `ollama pull llama3.2`
3. Check bot logs for errors

### Context Not Persisting

The agent uses user ID for context. Make sure:
- Same Telegram user sends messages
- Bot is not restarted (context is in-memory)

### Commands Not Working

Commands have higher priority (group=0) than agent (group=1).
If commands aren't working, check:
- Command handler registration in `handlers/commands.py`
- Bot token is correct

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  Telegram Bot                        │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │   Commands   │  │   Logging    │  │   Agent   │ │
│  │  (group=0)   │  │  (group=-1)  │  │(group=1)  │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
│         │                  │               │        │
│         │                  │               ▼        │
│         │                  │     ┌─────────────────┐│
│         │                  │     │ LangGraph Agent ││
│         │                  │     ├─────────────────┤│
│         │                  │     │ • Intent Class  ││
│         │                  │     │ • Entity Extract││
│         │                  │     │ • Follow-up Q   ││
│         │                  │     │ • Context Mgmt  ││
│         │                  │     └─────────────────┘│
│         │                  │               │        │
│         ▼                  ▼               ▼        │
│  ┌─────────────────────────────────────────────────┐│
│  │              Response to User                   ││
│  └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

## Next Steps

### Potential Enhancements

1. **Database Persistence**: Store conversation context in database
2. **Session Timeout**: Clear context after inactivity
3. **Analytics**: Track common queries and intents
4. **Multi-language Support**: Add support for other languages
5. **Voice Messages**: Process voice messages with Whisper

### Monitoring

Add logging to track:
- Most common intents
- Average conversation length
- Follow-up success rate
- User satisfaction

---

**Integration Status**: ✅ Complete and Ready to Use!

The bot now handles both slash commands AND natural language conversations seamlessly.
