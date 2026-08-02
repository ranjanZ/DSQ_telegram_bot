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
OLLAMA_MODEL = "gemma2:2b"
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
    """Classify user's intent based on conversation history."""
    import logging
    logger = logging.getLogger(__name__)
    
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
    
    logger.info(f"[CLASSIFY_INTENT] Raw LLM intent: '{intent}'")
    
    # Map variations to standard intents
    intent_map = {
        "get_license": ["get_license", "license", "create license", "generate key", "get key", "want license", "need license"],
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
    
    # Special case: if user says "yes" and previous context was about license, treat as get_license
    if intent in ["yes", "yeah", "sure", "ok", "okay"]:
        # Check if there's license-related context in recent messages
        recent_messages = list(state["messages"])[-3:]
        for msg in recent_messages:
            if isinstance(msg, AIMessage) and ("license" in msg.content.lower() or "proceed" in msg.content.lower()):
                final_intent = "get_license"
                logger.info(f"[CLASSIFY_INTENT] Detected affirmative response in license context, setting intent to get_license")
                break
    
    logger.info(f"[CLASSIFY_INTENT] Final intent: '{final_intent}'")
    return {**state, "intent": final_intent}


def extract_entities(state: AgentState) -> AgentState:
    """Extract entities like MT5 ID, Name, Broker, etc. from the conversation."""
    import logging
    logger = logging.getLogger(__name__)
    
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
    
    logger.info(f"[EXTRACT_ENTITIES] LLM response: '{response.content.strip()}'")
    
    try:
        # Clean response to ensure valid JSON
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3:]
            
        entities = json.loads(content.strip())
        # Merge with existing entities
        current_entities = state.get("entities", {})
        current_entities.update(entities)
        logger.info(f"[EXTRACT_ENTITIES] Extracted entities: {entities}, Merged: {current_entities}")
        return {**state, "entities": current_entities}
    except json.JSONDecodeError as e:
        logger.warning(f"[EXTRACT_ENTITIES] Failed to parse JSON: {e}, raw content: '{response.content.strip()}'")
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
    import logging
    logger = logging.getLogger(__name__)
    
    missing = state.get("missing_info", [])
    logger.info(f"[FOLLOWUP] Missing fields: {missing}")
    
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
    
    logger.info(f"[FOLLOWUP] Asking: '{question}'")
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
    import logging
    logger = logging.getLogger(__name__)
    
    missing = state.get("missing_info", [])
    entities = state.get("entities", {})
    
    logger.info(f"[EXECUTE_LICENSE] Missing: {missing}, Entities: {entities}")
    
    if missing:
        logger.warning(f"[EXECUTE_LICENSE] Cannot create license, missing fields: {missing}")
        return {**state, "action_taken": False}
        
    bot_version = entities.get("bot_version", "v2")
    logger.info(f"[EXECUTE_LICENSE] Creating license for version: {bot_version}")
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
        logger.info(f"[EXECUTE_LICENSE] License created successfully: {license_key[:8]}...")
        return {**state, "response": response, "action_taken": True}
    else:
        logger.error(f"[EXECUTE_LICENSE] Failed to create license")
        return {
            **state, 
            "response": "❌ Failed to create license. Please check your GitHub token permissions or try again later.",
            "action_taken": False
        }


def generate_response(state: AgentState) -> AgentState:
    """Generate a response for general queries or help."""
    import logging
    logger = logging.getLogger(__name__)
    
    intent = state.get("intent", "general")
    logger.info(f"[GENERATE_RESPONSE] Intent: '{intent}'")
    
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
    elif intent == "get_license":
        # This should not happen normally as get_license goes to execute_creation
        # But if we reach here, ask for more info
        response = (
            "I'd be happy to help you get a license!\n\n"
            "Please provide the following details:\n"
            "1. Your MetaTrader 5 Account ID (MT5 ID)\n"
            "2. Your full name\n"
            "3. Your broker's name\n"
            "4. Account type (Live or Demo)\n"
            "5. Which bot version? (V1, V2, V3, or V4)"
        )
    else:
        # Fallback generic response using LLM
        system_prompt = "You are the Dalal Street Quants assistant. Answer the user's query concisely and helpfully."
        messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
        resp = llm.invoke(messages)
        response = resp.content
        
    logger.info(f"[GENERATE_RESPONSE] Response generated: '{response[:80]}...'")
    return {**state, "response": response}


def route_logic(state: AgentState) -> Literal["ask_followup", "create_license", "send_response", "end"]:
    """Decide the next step based on state."""
    import logging
    logger = logging.getLogger(__name__)
    
    intent = state.get("intent", "")
    missing = state.get("missing_info", [])
    should_exit = state.get("should_exit", False)
    
    logger.info(f"[ROUTE_LOGIC] Intent: '{intent}', Missing: {missing}, ShouldExit: {should_exit}")
    
    if should_exit:
        return "end"
        
    if intent == "get_license":
        if not missing:
            logger.info(f"[ROUTE_LOGIC] Routing to create_license")
            return "create_license"
        else:
            logger.info(f"[ROUTE_LOGIC] Routing to ask_followup (missing: {missing})")
            return "ask_followup"
            
    logger.info(f"[ROUTE_LOGIC] Routing to send_response")
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
        import logging
        logger = logging.getLogger(__name__)
        history = self.conversations.get(user_id, [])
        logger.info(f"[CONVERSATION_MEMORY] get_history for user {user_id}: {len(history)} messages")
        return history
    
    def add_message(self, user_id: str, message: BaseMessage):
        import logging
        logger = logging.getLogger(__name__)
        if user_id not in self.conversations:
            self.conversations[user_id] = []
            logger.info(f"[CONVERSATION_MEMORY] Created new conversation for user {user_id}")
        self.conversations[user_id].append(message)
        
        # Keep only last 10 messages to avoid context overflow
        if len(self.conversations[user_id]) > 10:
            self.conversations[user_id] = self.conversations[user_id][-10:]
            logger.info(f"[CONVERSATION_MEMORY] Trimmed conversation for user {user_id} to 10 messages")
        
        logger.info(f"[CONVERSATION_MEMORY] Added message for user {user_id}, total: {len(self.conversations[user_id])} messages")
    
    def clear_history(self, user_id: str):
        import logging
        logger = logging.getLogger(__name__)
        if user_id in self.conversations:
            del self.conversations[user_id]
            logger.info(f"[CONVERSATION_MEMORY] Cleared history for user {user_id}")
        else:
            logger.info(f"[CONVERSATION_MEMORY] No history to clear for user {user_id}")
    
    def is_in_agent_mode(self, user_id: str) -> bool:
        import logging
        logger = logging.getLogger(__name__)
        result = self.modes.get(user_id, "command") == "agent"
        logger.info(f"[CONVERSATION_MEMORY] is_in_agent_mode for user {user_id}: {result}, current mode: {self.modes.get(user_id, 'command')}")
        return result
    
    def set_agent_mode(self, user_id: str, active: bool):
        import logging
        logger = logging.getLogger(__name__)
        self.modes[user_id] = "agent" if active else "command"
        logger.info(f"[CONVERSATION_MEMORY] set_agent_mode for user {user_id}: {'agent' if active else 'command'}")


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
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"[RUN_AGENT] User {user_id} sent message: '{user_message}'")
    logger.info(f"[RUN_AGENT] User {user_id} in agent mode: {memory.is_in_agent_mode(user_id)}")
    
    # Get conversation history
    history = memory.get_history(user_id)
    logger.info(f"[RUN_AGENT] Conversation history length: {len(history)}")
    
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
    
    logger.info(f"[RUN_AGENT] Invoking agent_app...")
    
    # Run the agent
    try:
        result = agent_app.invoke(initial_state)
        logger.info(f"[RUN_AGENT] Agent invocation successful")
    except Exception as e:
        logger.error(f"[RUN_AGENT] Agent invocation failed: {e}", exc_info=True)
        raise
    
    # Get response
    response = result.get("response", "Something went wrong.")
    logger.info(f"[RUN_AGENT] Agent response: '{response[:100]}...'")
    
    # Update conversation history
    memory.add_message(user_id, HumanMessage(content=user_message))
    memory.add_message(user_id, AIMessage(content=response))
    logger.info(f"[RUN_AGENT] Updated conversation history, new length: {len(memory.get_history(user_id))}")
    
    # Check if we should exit agent mode
    if result.get("should_exit"):
        logger.info(f"[RUN_AGENT] Exiting agent mode for user {user_id}")
        memory.set_agent_mode(user_id, False)
        memory.clear_history(user_id)
    
    return response


def enter_agent_mode(user_id: str) -> str:
    """Enter agent mode for a user."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[AGENT MODE] User {user_id} is entering agent mode")
    print(f"User {user_id} has entered agent mode.")

    memory.set_agent_mode(user_id, True)
    memory.clear_history(user_id)  # Clear old history when entering agent mode
    
    logger.info(f"[AGENT MODE] User {user_id} agent mode status: {memory.is_in_agent_mode(user_id)}")
    
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
