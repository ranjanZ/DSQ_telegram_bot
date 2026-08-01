"""
LangGraph-based Chat Agent powered by Ollama
This agent handles natural language queries for DSQ bot operations like:
- Getting license for DSQ V2, V3, V4
- Answering setup questions
- Providing risk information

Features:
- Intent classification
- Entity extraction
- Follow-up questions when information is missing
- Multi-turn conversation support with conversation history

Integration with Telegram:
- See telegram_integration.py for how to integrate with your Telegram bot
- The agent automatically handles non-command messages
- Conversation context is maintained per user ID
"""

from typing import TypedDict, Annotated, List, Any, Optional
from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
import operator

# Initialize Ollama model
llm = ChatOllama(
    model="llama3.2",  # or any other open-source model available in Ollama
    base_url="http://localhost:11434",
    temperature=0.7
)

# ==================== STATE DEFINITION ====================
class AgentState(TypedDict):
    messages: Annotated[List[str], operator.add]  # Conversation history
    user_query: str  # Current user query
    intent: str  # Classified intent
    bot_version: str  # Detected bot version
    mt5_id: str  # Extracted MT5 ID
    name: str  # Extracted name
    broker: str  # Extracted broker
    account_type: str  # Extracted account type
    response: str  # Final response
    needs_followup: bool  # Flag indicating if follow-up is needed
    missing_fields: List[str]  # List of missing required fields
    conversation_context: dict  # Stores context across turns


# ==================== INTENT CLASSIFICATION NODE ====================
def classify_intent(state: AgentState) -> AgentState:
    """Classify user intent from natural language query with conversation context."""
    query = state["user_query"]
    context = state.get("conversation_context", {})
    messages_history = state.get("messages", [])
    
    # Build context-aware prompt
    context_str = ""
    if context:
        context_str = f"\nPrevious conversation context:\n- Bot version mentioned: {context.get('bot_version', 'none')}\n- MT5 ID: {context.get('mt5_id', 'none')}\n- Name: {context.get('name', 'none')}\n- Broker: {context.get('broker', 'none')}\n- Account type: {context.get('account_type', 'none')}"
    
    prompt = f"""
    Classify the following user query into one of these intents:
    - get_license: User wants to get/create a license
    - setup_help: User needs help with setup
    - risk_info: User is asking about risk information
    - download_bot: User wants to download a bot
    - followup_answer: User is providing missing information in response to a follow-up question
    - general: General question or greeting
    
    Also identify which bot version they're asking about (v1, v2, v3, v4, or unknown).
    
    Current Query: {query}{context_str}
    
    Consider the conversation history and context when classifying.
    
    Respond in this format:
    INTENT: <intent>
    VERSION: <v1|v2|v3|v4|unknown>
    """
    
    response = llm.invoke(prompt)
    content = response.content.strip()
    
    intent = "general"
    version = "unknown"
    
    for line in content.split("\n"):
        if line.startswith("INTENT:"):
            intent = line.replace("INTENT:", "").strip()
        elif line.startswith("VERSION:"):
            version = line.replace("VERSION:", "").strip()
    
    # If no version detected but we have it in context, use context version
    if version == "unknown" and context.get("bot_version"):
        version = context["bot_version"]
    
    return {
        **state,
        "intent": intent,
        "bot_version": version,
        "messages": messages_history + [f"[System] Classified intent: {intent}, version: {version}"]
    }


# ==================== ENTITY EXTRACTION NODE ====================
def extract_entities(state: AgentState) -> AgentState:
    """Extract entities like MT5 ID, name, broker, account type from user query with context merging."""
    query = state["user_query"]
    context = state.get("conversation_context", {})
    messages_history = state.get("messages", [])
    
    # Get previously extracted entities from context
    prev_mt5_id = context.get("mt5_id", "")
    prev_name = context.get("name", "")
    prev_broker = context.get("broker", "")
    prev_account_type = context.get("account_type", "")
    
    prompt = f"""
    Extract the following information from the user query if available:
    - MT5 ID (numeric ID like 12345678)
    - Full Name
    - Broker name (XM, Vantage, Roboforex, Exness, etc.)
    - Account Type (Demo or Real)
    
    Current Query: {query}
    
    Previously extracted information (merge new info with this):
    - MT5 ID: {prev_mt5_id or 'None'}
    - Name: {prev_name or 'None'}
    - Broker: {prev_broker or 'None'}
    - Account Type: {prev_account_type or 'None'}
    
    Respond in this format (use 'None' if not found or not updated):
    MT5_ID: <value or None>
    NAME: <value or None>
    BROKER: <value or None>
    ACCOUNT_TYPE: <value or None>
    """
    
    response = llm.invoke(prompt)
    content = response.content.strip()
    
    mt5_id = ""
    name = ""
    broker = ""
    account_type = ""
    
    for line in content.split("\n"):
        if line.startswith("MT5_ID:") and "None" not in line:
            mt5_id = line.replace("MT5_ID:", "").strip()
        elif line.startswith("NAME:") and "None" not in line:
            name = line.replace("NAME:", "").strip()
        elif line.startswith("BROKER:") and "None" not in line:
            broker = line.replace("BROKER:", "").strip()
        elif line.startswith("ACCOUNT_TYPE:") and "None" not in line:
            account_type = line.replace("ACCOUNT_TYPE:", "").strip()
    
    # Merge with previous context - keep old values if new ones are empty
    mt5_id = mt5_id or prev_mt5_id
    name = name or prev_name
    broker = broker or prev_broker
    account_type = account_type or prev_account_type
    
    return {
        **state,
        "mt5_id": mt5_id,
        "name": name,
        "broker": broker,
        "account_type": account_type,
        "messages": messages_history + [f"[System] Extracted: MT5={mt5_id}, Name={name}, Broker={broker}, Type={account_type}"]
    }


# ==================== RESPONSE GENERATION NODES ====================
def handle_license_request(state: AgentState) -> AgentState:
    """Handle license creation requests with follow-up questions."""
    version = state["bot_version"]
    mt5_id = state["mt5_id"]
    name = state["name"]
    broker = state["broker"]
    account_type = state["account_type"]
    messages_history = state.get("messages", [])
    
    # Check if we have all required information
    missing_info = []
    if not mt5_id:
        missing_info.append("MT5 ID")
    if not name:
        missing_info.append("Name")
    if not broker:
        missing_info.append("Broker")
    if not account_type:
        missing_info.append("Account Type (Demo/Real)")
    
    if missing_info:
        # Need to ask follow-up questions
        response = f"""
To create a license for DSQ {version.upper()}, I need the following information:
- {chr(10).join('- ' + item for item in missing_info)}

Please provide these details. You can give me all at once or one at a time.

Partner codes to add before creating license:
• Vantage: VcM6U1DW
• Roboforex: zrfhm
• XM: 4299V
• Exness: c_niibgmkreg
        """
        needs_followup = True
    else:
        # Have all information - proceed with license creation
        response = f"""
Great! I have all the information needed for your DSQ {version.upper()} license:
- MT5 ID: {mt5_id}
- Name: {name}
- Broker: {broker}
- Account Type: {account_type}

To complete the license creation, please use:
/get_licence_{version.lower().replace('v', '')}

This will start an interactive process in the Telegram bot.

⚙️ After getting the license, remember to configure MetaTrader:
- Tools → Options → Expert Advisors
- Enable "Allow Algorithmic Trading"
- Add https://raw.githubusercontent.com to Web Request URL list
        """
        needs_followup = False
    
    # Update conversation context
    conversation_context = {
        "bot_version": version,
        "mt5_id": mt5_id,
        "name": name,
        "broker": broker,
        "account_type": account_type,
        "current_task": "license_creation"
    }
    
    return {
        **state,
        "response": response,
        "needs_followup": needs_followup,
        "missing_fields": missing_info,
        "conversation_context": conversation_context,
        "messages": messages_history + [f"[System] License request handled, followup needed: {needs_followup}"]
    }


def handle_setup_help(state: AgentState) -> AgentState:
    """Handle setup help requests."""
    version = state["bot_version"]
    version_num = version.lower().replace('v', '') if version != 'unknown' else '1'
    messages_history = state.get("messages", [])
    
    response = f"""
🛠️ DSQ V{version_num} Setup Guide:

1. Download & Login to MT5
   - Get MT5 from metatrader5.com
   - Login with your broker credentials

2. Configure MetaTrader
   - Tools → Options → Expert Advisors
   - ✅ Enable "Allow Algorithmic Trading"
   - ✅ Allow Web Request → Add: https://raw.githubusercontent.com

3. Download the Bot
   - Use /get_dsq_v{version_num} in Telegram
   - Double-click the downloaded .ex5 file

4. Activate License
   - Use /get_licence_v{version_num} in Telegram
   - Follow the interactive form (or tell me your details and I'll guide you)

📹 Video Tutorial: https://www.youtube.com/watch?v=AikfpXh4W4U
    """
    
    return {
        **state,
        "response": response,
        "needs_followup": False,
        "messages": messages_history + [f"[System] Setup help provided for V{version_num}"]
    }


def handle_risk_info(state: AgentState) -> AgentState:
    """Handle risk information requests."""
    version = state["bot_version"]
    version_num = version.lower().replace('v', '') if version != 'unknown' else '1'
    messages_history = state.get("messages", [])
    
    response = f"""
⚠️ DSQ V{version_num} Risk Information:

For traders with ~10,000 INR (≈100 USD):
→ Use a CENT Account (not USD)
→ 100 USD becomes 10,000 USC in cent account
→ Minimum deposit: $100

Compatible Cent Accounts:
- Vantage: cent STP (1:2000)
- XM: Micro account (1:1000)
- Roboforex: ProCent (1:2000)
- Exness: USC account

⚠️ Important:
- Test on Demo first
- Run only in sideways market
- Emergency stop: Press Ctrl+E in MetaTrader
- This bot is for Gold (XAUUSD) only
- Use default settings
    """
    
    return {
        **state,
        "response": response,
        "needs_followup": False,
        "messages": messages_history + [f"[System] Risk info provided for V{version_num}"]
    }


def handle_download_request(state: AgentState) -> AgentState:
    """Handle bot download requests."""
    version = state["bot_version"]
    version_num = version.lower().replace('v', '') if version != 'unknown' else '1'
    messages_history = state.get("messages", [])
    
    response = f"""
📦 Download DSQ V{version_num}:

Direct download link:
https://github.com/ranjanZ/DSQ_Page/raw/refs/heads/main/data/bots/dsq_v{version_num}.ex5

Or use the Telegram command:
/get_dsq_v{version_num}

Note: You'll need a valid license to use the bot.
Use /get_licence_v{version_num} to create your free license.
    """
    
    return {
        **state,
        "response": response,
        "needs_followup": False,
        "messages": messages_history + [f"[System] Download link provided for V{version_num}"]
    }


def handle_general(state: AgentState) -> AgentState:
    """Handle general queries and greetings."""
    query = state["user_query"]
    messages_history = state.get("messages", [])
    
    prompt = f"""
    Respond to this user query in a helpful and friendly manner.
    The user is asking about DSQ (Dalal Street Quants) trading bots.
    
    Available commands:
    - /get_licence_v1, /get_licence_v2, /get_licence_v3, /get_licence_v4 (create license)
    - /get_dsq_v1, /get_dsq_v2, /get_dsq_v3, /get_dsq_v4 (download bot)
    - /get_setup_instruction_v1, etc. (setup guide)
    - /risk_v1, /risk_v2, /risk_v3, /risk_v4 (risk info)
    
    Partner codes:
    - Vantage: VcM6U1DW
    - Roboforex: zrfhm
    - XM: 4299V
    - Exness: c_niibgmkreg
    
    Query: {query}
    
    Provide a helpful response. Keep it concise.
    """
    
    response = llm.invoke(prompt)
    
    return {
        **state,
        "response": response.content,
        "needs_followup": False,
        "messages": messages_history + [f"[System] General response provided"]
    }


# ==================== ROUTING FUNCTION ====================
def route_by_intent(state: AgentState) -> str:
    """Route to appropriate handler based on intent."""
    intent = state["intent"]
    
    if intent == "get_license":
        return "handle_license"
    elif intent == "setup_help":
        return "handle_setup"
    elif intent == "risk_info":
        return "handle_risk"
    elif intent == "download_bot":
        return "handle_download"
    else:
        return "handle_general"


# ==================== FOLLOW-UP CHECK FUNCTION ====================
def check_followup_needed(state: AgentState) -> str:
    """Check if follow-up is needed or conversation is complete."""
    if state.get("needs_followup", False):
        return "wait_for_followup"
    else:
        return "end_conversation"


# ==================== BUILD THE GRAPH ====================
def create_agent_graph():
    """Create and compile the LangGraph agent with follow-up support."""
    
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("extract_entities", extract_entities)
    workflow.add_node("handle_license", handle_license_request)
    workflow.add_node("handle_setup", handle_setup_help)
    workflow.add_node("handle_risk", handle_risk_info)
    workflow.add_node("handle_download", handle_download_request)
    workflow.add_node("handle_general", handle_general)
    
    # Set entry point
    workflow.set_entry_point("classify_intent")
    
    # Add edges
    workflow.add_edge("classify_intent", "extract_entities")
    
    # Add conditional routing after entity extraction
    workflow.add_conditional_edges(
        "extract_entities",
        route_by_intent,
        {
            "handle_license": "handle_license",
            "handle_setup": "handle_setup",
            "handle_risk": "handle_risk",
            "handle_download": "handle_download",
            "handle_general": "handle_general"
        }
    )
    
    # Add conditional edge for follow-up handling (only for license requests)
    workflow.add_conditional_edges(
        "handle_license",
        check_followup_needed,
        {
            "wait_for_followup": END,  # Will wait for user's next message
            "end_conversation": END
        }
    )
    
    # All other handlers lead to END
    workflow.add_edge("handle_setup", END)
    workflow.add_edge("handle_risk", END)
    workflow.add_edge("handle_download", END)
    workflow.add_edge("handle_general", END)
    
    return workflow.compile()


# ==================== MAIN AGENT INTERFACE ====================
class DSQChatAgent:
    """Main interface for the DSQ Chat Agent with multi-turn conversation support."""
    
    def __init__(self):
        self.graph = create_agent_graph()
        # Store conversation states per user
        self.conversation_states = {}
    
    def chat(self, user_query: str, user_id: str = "default") -> str:
        """
        Process a natural language query and return a response.
        Supports multi-turn conversations with context persistence.
        
        Args:
            user_query: The user's natural language question/request
            user_id: Unique identifier for the user (for conversation tracking)
            
        Returns:
            str: The agent's response
        """
        # Get or initialize conversation state for this user
        if user_id not in self.conversation_states:
            self.conversation_states[user_id] = {
                "messages": [],
                "conversation_context": {}
            }
        
        user_state = self.conversation_states[user_id]
        
        # Build initial state with conversation history
        initial_state = {
            "messages": user_state["messages"],
            "user_query": user_query,
            "intent": "",
            "bot_version": "unknown",
            "mt5_id": "",
            "name": "",
            "broker": "",
            "account_type": "",
            "response": "",
            "needs_followup": False,
            "missing_fields": [],
            "conversation_context": user_state.get("conversation_context", {})
        }
        
        # Run the graph
        result = self.graph.invoke(initial_state)
        
        # Update stored conversation state
        self.conversation_states[user_id] = {
            "messages": result["messages"],
            "conversation_context": result.get("conversation_context", {})
        }
        
        return result["response"]
    
    def reset_conversation(self, user_id: str = "default"):
        """Reset conversation history for a specific user."""
        if user_id in self.conversation_states:
            del self.conversation_states[user_id]
    
    def get_conversation_context(self, user_id: str = "default") -> dict:
        """Get the current conversation context for a user."""
        return self.conversation_states.get(user_id, {}).get("conversation_context", {})


# Example usage and testing
if __name__ == "__main__":
    print("=" * 60)
    print("DSQ Chat Agent - Multi-Turn Conversation Demo")
    print("=" * 60)
    print("\nThis demonstrates how the agent handles follow-up questions.")
    print("The agent will ask for missing information when needed.\n")
    
    agent = DSQChatAgent()
    
    # Test queries demonstrating multi-turn conversation
    print("=" * 60)
    print("Test 1: Multi-Turn Conversation with Follow-up Questions")
    print("=" * 60)
    
    # First turn: User wants license but doesn't provide all info
    query1 = "I want to get a license for dsq v2"
    print(f"\nUser: {query1}")
    response1 = agent.chat(query1, user_id="test_user")
    print(f"Agent: {response1}")
    
    # Second turn: User provides partial information
    query2 = "My MT5 ID is 12345678 and name is John Doe"
    print(f"\nUser: {query2}")
    response2 = agent.chat(query2, user_id="test_user")
    print(f"Agent: {response2}")
    
    # Third turn: User provides remaining information
    query3 = "Broker is XM and I want a Real account"
    print(f"\nUser: {query3}")
    response3 = agent.chat(query3, user_id="test_user")
    print(f"Agent: {response3}")
    
    print("\n" + "=" * 60)
    print("Test 2: Single-Turn with All Information")
    print("=" * 60)
    
    # Test with all information at once
    query_complete = "Get me a license for dsq v3. MT5 ID: 87654321, Name: Jane Smith, Broker: Vantage, Account: Demo"
    print(f"\nUser: {query_complete}")
    response_complete = agent.chat(query_complete, user_id="test_user_2")
    print(f"Agent: {response_complete}")
    
    print("\n" + "=" * 60)
    print("Note: To use with Telegram, see telegram_integration.py")
    print("=" * 60)
