"""
Dalal Street Quants LangGraph Agent
Self-sufficient agent that handles natural language queries and creates licenses automatically.

Features:
- Intent classification (get_license, setup_help, risk_info, download_bot, general, exit_agent)
- Entity extraction (mt5_id, name, broker, account_type, bot_version)
- Multi-turn conversations with automatic follow-up questions
- Self-sufficient license creation (creates JSON file and pushes to GitHub)
- Agent mode toggle via /agent_mode command
"""

import os
import json
import hashlib
import requests
from typing import TypedDict, Annotated, Sequence, Literal, Optional, Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from datetime import datetime

# Configuration
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
GITHUB_TOKEN = os.getenv("GITHUB_API_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "your-github-username")
GITHUB_REPO = os.getenv("GITHUB_REPO", "your-repo-name")
BRANCH_NAME = os.getenv("GITHUB_BRANCH", "main")

# Initialize LLM
llm = ChatOllama(model=OLLAMA_MODEL, temperature=0)


class AgentState(TypedDict):
    """State for the LangGraph agent."""
    messages: Annotated[Sequence[BaseMessage], "add_messages"]
    intent: str
    entities: Dict[str, Any]
    missing_info: list[str]
    response: str
    action_taken: bool
    should_exit: bool


def classify_intent(state: AgentState) -> AgentState:
    """Classify user intent based on conversation history."""
    system_prompt = """
You are the Dalal Street Quants (DSQ) Assistant.
Classify the user's intent into one of these categories:
- get_license: User wants to create/get a license key.
- setup_help: User needs help setting up the bot.
- risk_info: User asks about risk management.
- download_bot: User wants to download the bot file.
- general: General greeting or unrelated query.
- exit_agent: User wants to exit agent mode (keywords: exit, quit, menu, commands, /start).

Return ONLY the category name.
"""
    
    messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
    response = llm.invoke(messages)
    intent = response.content.strip().lower()
    
    # Map variations to standard intents
    intent_map = {
        "get_license": ["get_license", "license", "create license", "generate key", "get key"],
        "setup_help": ["setup_help", "setup", "install", "how to"],
        "risk_info": ["risk_info", "risk", "drawdown", "loss"],
        "download_bot": ["download_bot", "download", "get bot", "file"],
        "exit_agent": ["exit_agent", "exit", "quit", "menu", "commands", "/start", "stop agent"],
    }
    
    final_intent = "general"
    for standard, variations in intent_map.items():
        if any(var in intent for var in variations):
            final_intent = standard
            break
            
    return {**state, "intent": final_intent}


def extract_entities(state: AgentState) -> AgentState:
    """Extract entities like MT5 ID, Name, Broker, etc. from the conversation."""
    system_prompt = """
Extract the following entities from the user's message if present:
- mt5_id: MetaTrader 5 Account ID (numeric)
- name: User's full name
- broker: Broker name
- account_type: Account type (Live or Demo)
- bot_version: Bot version (v1, v2, v3, v4)

Return a JSON object with the found entities. If an entity is not found, do not include it.
Example: {"mt5_id": "12345678", "name": "John Doe", "broker": "IC Markets"}
"""
    
    messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
    response = llm.invoke(messages)
    
    try:
        # Clean response to ensure valid JSON
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
            
        entities = json.loads(content.strip())
        # Merge with existing entities
        current_entities = state.get("entities", {})
        current_entities.update(entities)
        return {**state, "entities": current_entities}
    except json.JSONDecodeError:
        return state


def check_missing_info(state: AgentState) -> AgentState:
    """Determine what information is missing for license creation."""
    required_fields = ["mt5_id", "name", "broker", "account_type"]
    current_entities = state.get("entities", {})
    
    missing = []
    for field in required_fields:
        if field not in current_entities:
            missing.append(field)
            
    return {**state, "missing_info": missing}


def generate_followup_question(state: AgentState) -> AgentState:
    """Generate a natural language follow-up question for missing info."""
    missing = state.get("missing_info", [])
    
    if not missing:
        return {**state, "response": "I have all the information needed."}
    
    field_map = {
        "mt5_id": "your MetaTrader 5 Account ID",
        "name": "your full name",
        "broker": "your broker's name",
        "account_type": "your account type (Live or Demo)"
    }
    
    next_field = missing[0]
    question = f"To proceed with your license, could you please provide {field_map.get(next_field, next_field)}?"
    
    return {**state, "response": question}


def create_license_file(entities: Dict[str, Any], bot_version: str) -> tuple[bool, str]:
    """
    Self-sufficient license creation: Creates the JSON file and pushes to GitHub.
    Mirrors the logic used in the Telegram bot handlers.
    
    Returns: (success: bool, license_key: str)
    """
    if not GITHUB_TOKEN:
        return False, ""
        
    mt5_id = entities.get("mt5_id")
    name = entities.get("name")
    broker = entities.get("broker")
    account_type = entities.get("account_type", "Demo")
    
    if not all([mt5_id, name, broker]):
        return False, ""
        
    # Generate License Key (Simple hash simulation similar to bot logic)
    unique_string = f"{mt5_id}{name}{broker}{datetime.now().strftime('%Y%m%d')}"
    license_key = hashlib.sha256(unique_string.encode()).hexdigest()[:16].upper()
    
    # Construct file path based on version
    version_map = {
        "v1": "DSQ_V1",
        "v2": "DSQ_V2",
        "v3": "DSQ_V3",
        "v4": "DSQ_V4"
    }
    folder_name = version_map.get(bot_version.lower(), "DSQ_V2")
    file_path = f"licenses/{folder_name}/{mt5_id}.json"
    
    # Content structure matching bot handlers
    license_data = {
        "mt5_id": str(mt5_id),
        "name": name,
        "broker": broker,
        "account_type": account_type,
        "license_key": license_key,
        "created_at": datetime.now().isoformat(),
        "version": bot_version.lower()
    }
    
    # GitHub API Logic
    api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{file_path}"
    
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Check if file exists to get SHA (for update) or create new
    response = requests.get(api_url, headers=headers)
    sha = None
    if response.status_code == 200:
        sha = response.json().get("sha")
    
    payload = {
        "message": f"feat: Add license for {name} ({mt5_id}) - {bot_version.upper()} via DSQ Agent",
        "content": json.dumps(license_data, indent=2),
        "branch": BRANCH_NAME
    }
    
    if sha:
        payload["sha"] = sha
        
    put_response = requests.put(api_url, headers=headers, json=payload)
    
    if put_response.status_code in [200, 201]:
        return True, license_key
    return False, ""


def execute_license_creation(state: AgentState) -> AgentState:
    """Attempt to create the license if all info is present."""
    missing = state.get("missing_info", [])
    entities = state.get("entities", {})
    
    if missing:
        return {**state, "action_taken": False}
        
    bot_version = entities.get("bot_version", "v2")
    success, license_key = create_license_file(entities, bot_version)
    
    if success:
        response = (
            f"✅ **License Created Successfully!**\n\n"
            f"👤 Name: {entities['name']}\n"
            f"🆔 MT5 ID: {entities['mt5_id']}\n"
            f"🏢 Broker: {entities['broker']}\n"
            f"📦 Version: {bot_version.upper()}\n\n"
            f"🔑 **Your License Key:**\n`{license_key}`\n\n"
            f"The license file has been pushed to the repository. You can now use this key in your MetaTrader terminal."
        )
        return {**state, "response": response, "action_taken": True}
    else:
        return {
            **state, 
            "response": "❌ Failed to create license. Please check your GitHub token permissions or try again later.",
            "action_taken": False
        }


def generate_response(state: AgentState) -> AgentState:
    """Generate a response for general queries or help."""
    intent = state.get("intent", "general")
    
    if intent == "setup_help":
        response = (
            "To set up the bot:\n"
            "1. Download the EA file from our repository.\n"
            "2. Attach it to your MT5 chart.\n"
            "3. Enter your license key when prompted.\n\n"
            "Would you like me to help you get a license first?"
        )
    elif intent == "risk_info":
        response = (
            "Our bots use strict risk management. Typically, risk per trade is set between 0.5% to 1%. "
            "You can adjust this in the EA inputs under 'RiskPercent'. "
            "Always start with lower risk and increase gradually."
        )
    elif intent == "download_bot":
        response = (
            "You can download the latest bot version from our GitHub repository.\n"
            "Which version are you looking for?\n"
            "- V1 (Legacy)\n"
            "- V2 (Current Stable)\n"
            "- V3 (New Features)\n"
            "- V4 (Latest Beta)"
        )
    elif intent == "exit_agent":
        response = "Exiting agent mode. You can now use standard commands like /start, /get_dsq_v2, etc."
        return {**state, "response": response, "should_exit": True}
    else:
        # Fallback generic response using LLM
        system_prompt = "You are the Dalal Street Quants assistant. Answer the user's query concisely and helpfully."
        messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
        resp = llm.invoke(messages)
        response = resp.content
        
    return {**state, "response": response}


def route_logic(state: AgentState) -> Literal["ask_followup", "create_license", "send_response", "end"]:
    """Decide the next step based on state."""
    if state.get("should_exit"):
        return "end"
        
    if state.get("intent") == "get_license":
        if not state.get("missing_info"):
            return "create_license"
        else:
            return "ask_followup"
            
    return "send_response"


# Build the Graph
workflow = StateGraph(AgentState)

workflow.add_node("classify_intent", classify_intent)
workflow.add_node("extract_entities", extract_entities)
workflow.add_node("check_missing_info", check_missing_info)
workflow.add_node("generate_followup", generate_followup_question)
workflow.add_node("execute_creation", execute_license_creation)
workflow.add_node("generate_response", generate_response)

workflow.set_entry_point("classify_intent")

workflow.add_conditional_edges(
    "check_missing_info",
    route_logic,
    {
        "ask_followup": "generate_followup",
        "create_license": "execute_creation",
        "send_response": "generate_response",
        "end": END
    }
)

workflow.add_edge("classify_intent", "extract_entities")
workflow.add_edge("extract_entities", "check_missing_info")
workflow.add_edge("generate_followup", END)
workflow.add_edge("execute_creation", END)
workflow.add_edge("generate_response", END)

agent_app = workflow.compile()


class ConversationMemory:
    """Simple in-memory conversation store for multi-turn support."""
    
    def __init__(self):
        self.conversations: Dict[str, List[BaseMessage]] = {}
        self.modes: Dict[str, str] = {}  # Track agent mode per user
    
    def get_history(self, user_id: str) -> List[BaseMessage]:
        return self.conversations.get(user_id, [])
    
    def add_message(self, user_id: str, message: BaseMessage):
        if user_id not in self.conversations:
            self.conversations[user_id] = []
        self.conversations[user_id].append(message)
        
        # Keep only last 10 messages to avoid context overflow
        if len(self.conversations[user_id]) > 10:
            self.conversations[user_id] = self.conversations[user_id][-10:]
    
    def clear_history(self, user_id: str):
        if user_id in self.conversations:
            del self.conversations[user_id]
    
    def is_in_agent_mode(self, user_id: str) -> bool:
        return self.modes.get(user_id, "command") == "agent"
    
    def set_agent_mode(self, user_id: str, active: bool):
        self.modes[user_id] = "agent" if active else "command"


# Global memory instance
memory = ConversationMemory()


def run_agent(user_message: str, user_id: str) -> str:
    """
    Run the agent with a user message.
    
    Args:
        user_message: The user's input message
        user_id: Unique identifier for the user (for conversation memory)
    
    Returns:
        The agent's response text
    """
    # Get conversation history
    history = memory.get_history(user_id)
    
    # Create initial state
    initial_state = {
        "messages": history + [HumanMessage(content=user_message)],
        "intent": "",
        "entities": {},
        "missing_info": [],
        "response": "",
        "action_taken": False,
        "should_exit": False
    }
    
    # Run the agent
    result = agent_app.invoke(initial_state)
    
    # Get response
    response = result.get("response", "Something went wrong.")
    
    # Update conversation history
    memory.add_message(user_id, HumanMessage(content=user_message))
    memory.add_message(user_id, AIMessage(content=response))
    
    # Check if we should exit agent mode
    if result.get("should_exit"):
        memory.set_agent_mode(user_id, False)
        memory.clear_history(user_id)
    
    return response


def enter_agent_mode(user_id: str) -> str:
    """Enter agent mode for a user."""
    memory.set_agent_mode(user_id, True)
    memory.clear_history(user_id)  # Clear old history when entering agent mode
    
    return (
        "🤖 **Agent Mode Activated!**\n\n"
        "I'm now your personal Dalal Street Quants assistant. You can ask me anything in natural language!\n\n"
        "Examples:\n"
        "• 'I want to get a license for DSQ V2'\n"
        "• 'How do I set up the bot?'\n"
        "• 'What's the risk management strategy?'\n"
        "• 'Download V3 bot'\n\n"
        "Type 'exit' or 'menu' to return to command mode."
    )


def exit_agent_mode(user_id: str) -> str:
    """Exit agent mode for a user."""
    memory.set_agent_mode(user_id, False)
    memory.clear_history(user_id)
    
    return "Exited agent mode. Use /start to see available commands."


def is_in_agent_mode(user_id: str) -> bool:
    """Check if a user is in agent mode."""
    return memory.is_in_agent_mode(user_id)
