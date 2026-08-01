# DSQ Chat Agent

A LangGraph-based chat agent powered by Ollama (open-source LLM) that handles natural language queries for DSQ (Dalal Street Quants) bot operations.

## Features

- **Natural Language Processing**: Understand user queries in plain English
- **Intent Classification**: Automatically detects what the user wants:
  - Get/create license for DSQ V1-V4
  - Setup help and instructions
  - Risk information
  - Bot download links
  - General questions
- **Entity Extraction**: Extracts MT5 ID, name, broker, account type from queries
- **Multi-version Support**: Handles all DSQ bot versions (V1, V2, V3, V4)

## Requirements

1. **Ollama**: Install and run Ollama locally
   ```bash
   # Install Ollama (Linux/Mac)
   curl -fsSL https://ollama.com/install.sh | sh
   
   # Pull a model (e.g., llama3.2)
   ollama pull llama3.2
   
   # Start Ollama server
   ollama serve
   ```

2. **Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

```python
from chat_agent.agent import DSQChatAgent

# Initialize the agent
agent = DSQChatAgent()

# Chat with the agent
response = agent.chat("I want to get a license for dsq v2")
print(response)
```

### Example Queries

The agent can handle various natural language queries:

- "I need a license for DSQ V2"
- "How do I set up the bot?"
- "What are the risks with this trading bot?"
- "Download V3 bot please"
- "My MT5 ID is 12345678, I use XM broker, can you help me get a license?"
- "Hello, what can you help me with?"

## Architecture

The agent uses a LangGraph workflow with the following nodes:

1. **classify_intent**: Determines user intent (get_license, setup_help, risk_info, download_bot, general)
2. **extract_entities**: Extracts relevant information (MT5 ID, name, broker, account type)
3. **handle_license**: Provides license creation guidance
4. **handle_setup**: Returns setup instructions
5. **handle_risk**: Provides risk information
6. **handle_download**: Returns download links
7. **handle_general**: Handles greetings and general questions

## Integration with Telegram Bot

To integrate this agent with your Telegram bot:

```python
from chat_agent.agent import DSQChatAgent
from telegram import Update
from telegram.ext import MessageHandler, filters

agent = DSQChatAgent()

async def handle_natural_language(update: Update, context):
    user_query = update.message.text
    response = agent.chat(user_query)
    await update.message.reply_text(response)

# Add to your bot handlers
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_natural_language))
```

## Configuration

Edit `agent.py` to customize:

- **Model**: Change `model="llama3.2"` to any Ollama model
- **Base URL**: Modify if Ollama runs on different host/port
- **Temperature**: Adjust response randomness (0.0 - 1.0)
- **Prompts**: Customize classification and response prompts

## Partner Codes Reference

The agent includes these partner codes in responses:
- Vantage: `VcM6U1DW`
- Roboforex: `zrfhm`
- XM: `4299V`
- Exness: `c_niibgmkreg`

## License

Same as the main DSQ project.
