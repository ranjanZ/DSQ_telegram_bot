# Dalal Street Quants AI Agent

A LangGraph-based AI agent powered by Ollama that handles natural language queries for DSQ bot operations.

## Features

- **Natural Language Understanding**: Process user queries in plain English/Hindi
- **Multi-turn Conversations**: Maintain context across multiple messages
- **Automatic Follow-up Questions**: Ask for missing information intelligently
- **Self-Sufficient License Creation**: Automatically create and push license files to GitHub
- **Agent Mode Toggle**: Enable/disable via `/agent_mode` command

## Quick Start

### 1. Enter Agent Mode
```
/agent_mode
```

### 2. Chat Naturally
```
I want to get a license for DSQ V2
My name is John Doe
MT5 ID: 12345678
Broker: IC Markets
Account type: Demo
```

### 3. Exit Agent Mode
```
exit
```
or use any command like `/start`

## Capabilities

The agent handles:

1. **License Creation** - Extracts MT5 ID, Name, Broker, Account Type and creates license automatically
2. **Setup Help** - Provides installation and setup guidance
3. **Risk Information** - Explains risk management strategies
4. **Bot Downloads** - Directs to appropriate download links (V1-V4)
5. **General Queries** - Answers questions about DSQ bots

## Example Conversation

```
User: /agent_mode

Bot: 🤖 **Agent Mode Activated!**
     I'm now your personal Dalal Street Quants assistant...

User: I want to get a license for DSQ V2

Bot: To proceed with your license, could you please provide your full name?

User: John Doe

Bot: To proceed with your license, could you please provide your MetaTrader 5 Account ID?

User: 12345678

Bot: To proceed with your license, could you please provide your broker's name?

User: IC Markets

Bot: To proceed with your license, could you please provide your account type (Live or Demo)?

User: Demo

Bot: ✅ **License Created Successfully!**
     
     👤 Name: John Doe
     🆔 MT5 ID: 12345678
     🏢 Broker: IC Markets
     📦 Version: V2
     
     🔑 **Your License Key:**
     `A1B2C3D4E5F6G7H8`
     
     The license file has been pushed to the repository.
```

## Environment Setup

Set these environment variables:

```bash
OLLAMA_MODEL=llama3
GITHUB_API_TOKEN=your_github_token
GITHUB_OWNER=your_github_username
GITHUB_REPO=your_repo_name
GITHUB_BRANCH=main
```

## How It Works

The agent uses a state machine workflow:

1. **Classify Intent** - Determines what the user wants (license, help, info, etc.)
2. **Extract Entities** - Pulls structured data from natural language (MT5 ID, name, etc.)
3. **Check Missing Info** - Identifies what information is still needed
4. **Follow-up or Execute** - Either asks for more info or creates the license
5. **Respond** - Sends formatted response back to user

## Self-Sufficient License Creation

When all required information is collected, the agent:
- Generates a unique license key using SHA256 hash
- Creates a JSON file with user details
- Pushes the file to your GitHub repository automatically
- Returns the license key to the user

File structure: `licenses/DSQ_V{version}/{mt5_id}.json`

## Integration

Already integrated in `bot.py`:
- `/agent_mode` command activates agent mode
- All text messages are processed by the agent when in agent mode
- Commands always work (priority over agent)
- Agent maintains conversation history per user

## Requirements

```bash
pip install langgraph langchain-ollama requests python-telegram-bot
```

Make sure Ollama is running with the required model:
```bash
ollama pull llama3
ollama serve
```
