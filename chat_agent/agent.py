"""
LangGraph-based Chat Agent powered by Ollama
This agent handles natural language queries for DSQ bot operations like:
- Getting license for DSQ V2, V3, V4
- Answering setup questions
- Providing risk information
"""

from typing import TypedDict, Annotated, List, Any
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
    messages: Annotated[List[str], operator.add]
    user_query: str
    intent: str
    bot_version: str
    mt5_id: str
    name: str
    broker: str
    account_type: str
    response: str


# ==================== INTENT CLASSIFICATION NODE ====================
def classify_intent(state: AgentState) -> AgentState:
    """Classify user intent from natural language query."""
    query = state["user_query"]
    
    prompt = f"""
    Classify the following user query into one of these intents:
    - get_license: User wants to get/create a license
    - setup_help: User needs help with setup
    - risk_info: User is asking about risk information
    - download_bot: User wants to download a bot
    - general: General question or greeting
    
    Also identify which bot version they're asking about (v1, v2, v3, v4, or unknown).
    
    Query: {query}
    
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
    
    return {
        **state,
        "intent": intent,
        "bot_version": version,
        "messages": [f"Classified intent: {intent}, version: {version}"]
    }


# ==================== ENTITY EXTRACTION NODE ====================
def extract_entities(state: AgentState) -> AgentState:
    """Extract entities like MT5 ID, name, broker, account type from user query."""
    query = state["user_query"]
    
    prompt = f"""
    Extract the following information from the user query if available:
    - MT5 ID (numeric ID like 12345678)
    - Full Name
    - Broker name (XM, Vantage, Roboforex, Exness, etc.)
    - Account Type (Demo or Real)
    
    Query: {query}
    
    Respond in this format (use 'None' if not found):
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
    
    return {
        **state,
        "mt5_id": mt5_id,
        "name": name,
        "broker": broker,
        "account_type": account_type,
        "messages": [f"Extracted entities: MT5={mt5_id}, Name={name}, Broker={broker}, Type={account_type}"]
    }


# ==================== RESPONSE GENERATION NODES ====================
def handle_license_request(state: AgentState) -> AgentState:
    """Handle license creation requests."""
    version = state["bot_version"]
    mt5_id = state["mt5_id"]
    name = state["name"]
    broker = state["broker"]
    account_type = state["account_type"]
    
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
        response = f"""
To create a license for DSQ {version.upper()}, I need the following information:
- {chr(10).join('- ' + item for item in missing_info)}

Please provide these details, or use the command /get_licence_{version.lower().replace('v', '')} 
in the Telegram bot for an interactive form.

Partner codes to add before creating license:
• Vantage: VcM6U1DW
• Roboforex: zrfhm
• XM: 4299V
• Exness: c_niibgmkreg
        """
    else:
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
    
    return {**state, "response": response}


def handle_setup_help(state: AgentState) -> AgentState:
    """Handle setup help requests."""
    version = state["bot_version"]
    version_num = version.lower().replace('v', '') if version != 'unknown' else '1'
    
    response = f"""
🛠️ DSQ V{version_num} Setup Guide:

1. Download & Login to MT5
   - Get MT5 from metatrader5.com
   - Login with your broker credentials

2. Configure MetaTrader
   - Tools → Options → Expert Advisors
   - ✅ Allow Algorithmic Trading
   - ✅ Allow Web Request → Add: https://raw.githubusercontent.com

3. Download the Bot
   - Use /get_dsq_v{version_num} in Telegram
   - Double-click the downloaded .ex5 file

4. Activate License
   - Use /get_licence_v{version_num} in Telegram
   - Follow the interactive form

📹 Video Tutorial: https://www.youtube.com/watch?v=AikfpXh4W4U
    """
    
    return {**state, "response": response}


def handle_risk_info(state: AgentState) -> AgentState:
    """Handle risk information requests."""
    version = state["bot_version"]
    version_num = version.lower().replace('v', '') if version != 'unknown' else '1'
    
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
    
    return {**state, "response": response}


def handle_download_request(state: AgentState) -> AgentState:
    """Handle bot download requests."""
    version = state["bot_version"]
    version_num = version.lower().replace('v', '') if version != 'unknown' else '1'
    
    response = f"""
📦 Download DSQ V{version_num}:

Direct download link:
https://github.com/ranjanZ/DSQ_Page/raw/refs/heads/main/data/bots/dsq_v{version_num}.ex5

Or use the Telegram command:
/get_dsq_v{version_num}

Note: You'll need a valid license to use the bot.
Use /get_licence_v{version_num} to create your free license.
    """
    
    return {**state, "response": response}


def handle_general(state: AgentState) -> AgentState:
    """Handle general queries and greetings."""
    query = state["user_query"]
    
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
    
    Provide a helpful response.
    """
    
    response = llm.invoke(prompt)
    
    return {**state, "response": response.content}


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


# ==================== BUILD THE GRAPH ====================
def create_agent_graph():
    """Create and compile the LangGraph agent."""
    
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
    
    # All handlers lead to END
    workflow.add_edge("handle_license", END)
    workflow.add_edge("handle_setup", END)
    workflow.add_edge("handle_risk", END)
    workflow.add_edge("handle_download", END)
    workflow.add_edge("handle_general", END)
    
    return workflow.compile()


# ==================== MAIN AGENT INTERFACE ====================
class DSQChatAgent:
    """Main interface for the DSQ Chat Agent."""
    
    def __init__(self):
        self.graph = create_agent_graph()
    
    def chat(self, user_query: str) -> str:
        """
        Process a natural language query and return a response.
        
        Args:
            user_query: The user's natural language question/request
            
        Returns:
            str: The agent's response
        """
        initial_state = {
            "messages": [],
            "user_query": user_query,
            "intent": "",
            "bot_version": "unknown",
            "mt5_id": "",
            "name": "",
            "broker": "",
            "account_type": "",
            "response": ""
        }
        
        result = self.graph.invoke(initial_state)
        return result["response"]


# Example usage
if __name__ == "__main__":
    agent = DSQChatAgent()
    
    # Test queries
    test_queries = [
        "I want to get a license for dsq v2",
        "How do I set up the bot?",
        "What are the risks?",
        "Download v3 bot please",
        "Hello!"
    ]
    
    for query in test_queries:
        print(f"\nUser: {query}")
        response = agent.chat(query)
        print(f"Agent: {response}")
        print("-" * 50)
