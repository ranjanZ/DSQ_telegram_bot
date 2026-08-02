"""
Dalal Street Quants - Clean Conversational Agent
Uses Gemma2:2b via Ollama for intent + entity understanding.
Handles: License creation (multi-turn), Setup help, General queries.
"""

import os
import json
import hashlib
import requests
from typing import TypedDict, Annotated, Sequence, Literal
from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from datetime import datetime

# ─── Configuration ─────────────────────────────────────────────
OLLAMA_MODEL = "gemma2:2b"
GITHUB_TOKEN = os.getenv("GITHUB_API_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "your-github-username")
GITHUB_REPO = os.getenv("GITHUB_REPO", "your-repo-name")
BRANCH_NAME = os.getenv("GITHUB_BRANCH", "main")

llm = ChatOllama(model=OLLAMA_MODEL, temperature=0.1)

# ─── State ─────────────────────────────────────────────────────
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "add_messages"]
    intent: Literal["license", "setup", "general", "exit", "unknown"]
    collected: dict
    missing: list
    action_result: dict
    response: str
    done: bool


# ─── Node 1: Understand ────────────────────────────────────────
UNDERSTAND_PROMPT = """You are the Dalal Street Quants AI Assistant. Analyze the conversation and output a JSON object.

Your job is to determine:
1. What the user wants (intent)
2. What information they've already provided
3. What's still missing (if anything)

Possible intents:
- "license": User wants to create a license key
- "setup": User wants setup instructions for a bot
- "general": General question about the bot, trading, risk, etc.
- "exit": User wants to exit agent mode (say exit, quit, menu, stop)
- "unknown": Cannot determine intent

For license creation, these fields are REQUIRED:
- mt5_id: MetaTrader 5 account number
- name: User's full name  
- broker: Broker name
- account_type: "Live" or "Demo"
- version: "v1", "v2", "v3", or "v4" (default to "v2" if not specified)

For setup help, try to extract:
- version: Which bot version they need help with

Output STRICT JSON in this exact format:
{
  "intent": "license|setup|general|exit|unknown",
  "collected": {"mt5_id": "...", "name": "...", ...},
  "missing": ["field1", "field2"],
  "reasoning": "Brief explanation of your decision"
}

Rules:
- Only include fields in "collected" if the user actually provided them in this or previous messages.
- "missing" should list required fields not yet collected.
- If intent is "general" or "exit", "missing" should be empty.
- If the user corrects previous info, update "collected" accordingly.
"""

def understand(state: AgentState) -> AgentState:
    """Single node: classify intent, extract entities, find gaps."""

    messages = [SystemMessage(content=UNDERSTAND_PROMPT)] + list(state["messages"])
    raw = llm.invoke(messages).content.strip()

    # Clean markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1].replace("json", "").strip()

    try:
        parsed = json.loads(raw)
        intent = parsed.get("intent", "unknown")
        collected = parsed.get("collected", {})
        missing = parsed.get("missing", [])
    except json.JSONDecodeError:
        intent, collected, missing = "unknown", {}, []

    # Merge newly collected with previous state
    prev_collected = state.get("collected", {})
    prev_collected.update(collected)

    # Re-check missing against merged data for license intent
    if intent == "license":
        required = ["mt5_id", "name", "broker", "account_type"]
        missing = [f for f in required if f not in prev_collected or not prev_collected[f]]
        if "version" not in prev_collected:
            prev_collected["version"] = "v2"

    return {
        **state,
        "intent": intent,
        "collected": prev_collected,
        "missing": missing,
    }


# ─── Node 2: Execute ───────────────────────────────────────────
def execute(state: AgentState) -> AgentState:
    """Execute the appropriate action based on intent and collected data."""

    intent = state["intent"]
    collected = state.get("collected", {})
    missing = state.get("missing", [])

    result = {"type": "none", "data": {}}

    # ── EXIT ──
    if intent == "exit":
        result = {"type": "exit", "data": {}}

    # ── LICENSE ──
    elif intent == "license":
        if missing:
            field_labels = {
                "mt5_id": "your MetaTrader 5 Account ID",
                "name": "your full name",
                "broker": "your broker's name", 
                "account_type": "your account type (Live or Demo)"
            }
            # Ask for ALL missing fields at once
            missing_labels = [field_labels.get(f, f) for f in missing]
            if len(missing_labels) == 1:
                question = f"To create your license, I still need {missing_labels[0]}. Could you please provide that?"
            else:
                question = (
                    "To create your license, I need the following information:"
                    + "\n".join(f"• {label}" for label in missing_labels)
                    + "\n\nPlease provide these details and I'll generate your license key right away."
                )
            result = {
                "type": "ask",
                "data": {"question": question}
            }
        else:
            success, license_key = _create_license_on_github(collected)
            if success:
                result = {
                    "type": "license_created",
                    "data": {
                        "license_key": license_key,
                        "mt5_id": collected["mt5_id"],
                        "name": collected["name"],
                        "broker": collected["broker"],
                        "version": collected.get("version", "v2").upper()
                    }
                }
            else:
                result = {
                    "type": "error",
                    "data": {"message": "Failed to create license. GitHub token may be missing or invalid."}
                }

    # ── SETUP ──
    elif intent == "setup":
        version = collected.get("version", "v2").lower()
        result = {
            "type": "setup_instructions",
            "data": {
                "version": version.upper(),
                "instructions": _get_setup_instructions(version)
            }
        }

    # ── GENERAL ──
    elif intent == "general":
        answer = _answer_general(state["messages"])
        result = {"type": "general_answer", "data": {"answer": answer}}

    # ── UNKNOWN ──
    else:
        result = {
            "type": "ask",
            "data": {
                "question": "I'm not sure I understood. I can help you with:\n1. Creating a license\n2. Bot setup instructions\n3. General questions about our bots\n\nWhat would you like to do?"
            }
        }

    return {**state, "action_result": result}


# ─── Node 3: Respond ───────────────────────────────────────────
RESPONSE_TEMPLATES = {
    "exit": "Exiting agent mode. You can use /start to see the menu. Goodbye! 👋",
    "ask": "{question}",
    "license_created": (
        "✅ **License Created Successfully!**\n\n"
        "👤 Name: {name}\n"
        "🆔 MT5 ID: {mt5_id}\n"
        "🏢 Broker: {broker}\n"
        "📦 Version: {version}\n\n"
        "🔑 **Your License Key:**\n`{license_key}`\n\n"
        "The license has been saved to the repository. Paste this key into your MetaTrader EA inputs."
    ),
    "error": "❌ {message}",
    "setup_instructions": (
        "📘 **Setup Instructions for DSQ {version}**\n\n"
        "{instructions}\n\n"
        "Need a license key next? Just say 'I want a license'!"
    ),
    "general_answer": "{answer}",
}

def respond(state: AgentState) -> AgentState:
    """Format the action result into a human-friendly response."""

    result = state.get("action_result", {})
    result_type = result.get("type", "none")
    data = result.get("data", {})

    template = RESPONSE_TEMPLATES.get(result_type, "I'm here to help! What would you like to do?")
    response = template.format(**data)

    return {**state, "response": response, "done": result_type in ["exit", "license_created", "setup_instructions", "general_answer", "error"]}


# ─── Router ────────────────────────────────────────────────────
def router(state: AgentState) -> Literal["execute", "end"]:
    """Decide next step after understanding."""
    if state["intent"] == "exit":
        return "end"
    return "execute"


# ─── Helper: License Creation ──────────────────────────────────
def _create_license_on_github(collected: dict) -> tuple[bool, str]:
    """Create license JSON and push to GitHub. Returns (success, license_key)."""

    if not GITHUB_TOKEN:
        return False, ""

    mt5_id = str(collected["mt5_id"])
    name = collected["name"]
    broker = collected["broker"]
    account_type = collected.get("account_type", "Demo")
    version = collected.get("version", "v2").lower()

    unique = f"{mt5_id}{name}{broker}{datetime.now().strftime('%Y%m%d')}"
    license_key = hashlib.sha256(unique.encode()).hexdigest()[:16].upper()

    folder = f"DSQ_{version.upper()}"
    file_path = f"licenses/{folder}/{mt5_id}.json"

    license_data = {
        "mt5_id": mt5_id,
        "name": name,
        "broker": broker,
        "account_type": account_type,
        "license_key": license_key,
        "created_at": datetime.now().isoformat(),
        "version": version
    }

    api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{file_path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    sha = None
    get_resp = requests.get(api_url, headers=headers)
    if get_resp.status_code == 200:
        sha = get_resp.json().get("sha")

    payload = {
        "message": f"license: {name} ({mt5_id}) - {version.upper()}",
        "content": json.dumps(license_data, indent=2),
        "branch": BRANCH_NAME
    }
    if sha:
        payload["sha"] = sha

    put_resp = requests.put(api_url, headers=headers, json=payload)
    return put_resp.status_code in [200, 201], license_key


# ─── Helper: Setup Instructions ────────────────────────────────
def _get_setup_instructions(version: str) -> str:
    instructions = {
        "v1": (
            "1. Download `DSQ_V1.ex5` from the repository.\n"
            "2. Open MetaTrader 5 → File → Open Data Folder → MQL5 → Experts.\n"
            "3. Copy the .ex5 file into the Experts folder.\n"
            "4. Restart MT5, then drag DSQ_V1 onto your chart.\n"
            "5. In the EA inputs, enter your license key and set RiskPercent (default 1%)."
        ),
        "v2": (
            "1. Download `DSQ_V2.ex5` from the repository.\n"
            "2. Open MT5 → File → Open Data Folder → MQL5 → Experts.\n"
            "3. Paste the file and restart MT5.\n"
            "4. Attach DSQ_V2 to a chart (recommended: EURUSD H1).\n"
            "5. Enter your license key. Set lot size mode: Fixed or Risk-based.\n"
            "6. Enable 'Allow Algo Trading' (green button on toolbar)."
        ),
        "v3": (
            "1. Download `DSQ_V3.ex5` and `DSQ_V3_Settings.set`.\n"
            "2. Place .ex5 in MQL5/Experts and .set in MQL5/Presets.\n"
            "3. Restart MT5, attach DSQ_V3 to chart.\n"
            "4. Load the preset: Inputs → Load → select DSQ_V3_Settings.set.\n"
            "5. Enter your license key. V3 includes auto-news-filter — ensure 'Allow WebRequest' is enabled."
        ),
        "v4": (
            "1. Download `DSQ_V4_Beta.ex5` from the beta branch.\n"
            "2. Install in MT5 Experts folder and restart.\n"
            "3. Attach to chart. V4 uses multi-pair logic — attach to ONE chart only.\n"
            "4. Enter license key. V4 auto-detects pairs; ensure all desired pairs are visible in Market Watch.\n"
            "5. Beta feature: Dashboard panel appears on chart. Risk settings are in the 'Advanced' tab."
        ),
    }
    return instructions.get(version, instructions["v2"])


# ─── Helper: General Answers ───────────────────────────────────
def _answer_general(messages: Sequence[BaseMessage]) -> str:
    """Use LLM to answer general questions with DSQ context."""
    system = (
        "You are the Dalal Street Quants support assistant. "
        "Answer trading/bot questions concisely and accurately. "
        "If unsure, say so honestly. Keep responses under 150 words."
    )
    msgs = [SystemMessage(content=system)] + list(messages[-6:])
    return llm.invoke(msgs).content.strip()


# ─── Build Graph ───────────────────────────────────────────────
workflow = StateGraph(AgentState)

workflow.add_node("understand", understand)
workflow.add_node("execute", execute)
workflow.add_node("respond", respond)

workflow.set_entry_point("understand")
workflow.add_conditional_edges("understand", router, {
    "execute": "execute",
    "end": END
})
workflow.add_edge("execute", "respond")
workflow.add_edge("respond", END)

agent_graph = workflow.compile()


# ─── Conversation Memory ───────────────────────────────────────
class ConversationMemory:
    def __init__(self):
        self.chats: dict[str, list[BaseMessage]] = {}
        self.modes: dict[str, bool] = {}

    def get(self, user_id: str) -> list[BaseMessage]:
        return self.chats.get(user_id, []).copy()

    def add(self, user_id: str, msg: BaseMessage):
        if user_id not in self.chats:
            self.chats[user_id] = []
        self.chats[user_id].append(msg)
        if len(self.chats[user_id]) > 10:
            self.chats[user_id] = self.chats[user_id][-10:]

    def clear(self, user_id: str):
        self.chats.pop(user_id, None)

    def is_agent(self, user_id: str) -> bool:
        return self.modes.get(user_id, False)

    def set_agent(self, user_id: str, active: bool):
        self.modes[user_id] = active
        if active:
            self.clear(user_id)


memory = ConversationMemory()


# ─── Public API ────────────────────────────────────────────────
def enter_agent_mode(user_id: str) -> str:
    memory.set_agent(user_id, True)
    return (
        "🤖 **Agent Mode On!**\n\n"
        "Talk to me naturally. I can help you with:\n"
        "• **License** — \"I want a license for V2\"\n"
        "• **Setup** — \"How do I install DSQ V3?\"\n"
        "• **General** — \"What's the risk setting?\"\n\n"
        "Say **exit** to leave agent mode."
    )


def run_agent(user_message: str, user_id: str) -> str:
    """Main entry point. Run one turn of the agent."""

    history = memory.get(user_id)
    current_messages = history + [HumanMessage(content=user_message)]

    initial_state: AgentState = {
        "messages": current_messages,
        "intent": "unknown",
        "collected": {},
        "missing": [],
        "action_result": {},
        "response": "",
        "done": False
    }

    result = agent_graph.invoke(initial_state)
    response = result.get("response", "I'm here to help!")

    memory.add(user_id, HumanMessage(content=user_message))
    memory.add(user_id, AIMessage(content=response))

    if result.get("intent") == "exit":
        memory.set_agent(user_id, False)
        memory.clear(user_id)

    return response


def is_in_agent_mode(user_id: str) -> bool:
    return memory.is_agent(user_id)


def exit_agent_mode(user_id: str) -> str:
    memory.set_agent(user_id, False)
    memory.clear(user_id)
    return "Exited agent mode. Use /start for the command menu."


# ═══════════════════════════════════════════════════════════════
# ═══ TESTING BLOCK ═════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """
    Run this file to test the agent:

        python dsq_agent.py

    Requirements:
        - Ollama running locally with gemma2:2b pulled
        - GITHUB_TOKEN set (or license creation will show error)
    """

    def run_test_scenario(name: str, user_id: str, inputs: list[str]):
        print("\n" + "=" * 70)
        print(f"  TEST SCENARIO: {name}")
        print("=" * 70)

        # Reset user
        memory.clear(user_id)
        memory.set_agent(user_id, True)

        # Welcome message
        print(f"\n🤖 Agent: {enter_agent_mode(user_id)}")

        for i, user_msg in enumerate(inputs, 1):
            print(f"\n--- Turn {i} ---")
            print(f"👤 User: {user_msg}")

            try:
                response = run_agent(user_msg, user_id)
                print(f"🤖 Agent: {response}")
            except Exception as e:
                print(f"❌ ERROR: {e}")
                break

        print(f"\n{'=' * 70}")
        print(f"  END OF {name}")
        print(f"{'=' * 70}\n")


    # # ── TEST 1: General Query ─────────────────────────────────
    # run_test_scenario(
    #     name="General Query",
    #     user_id="test_general_user",
    #     inputs=[
    #         "What is the risk management strategy in DSQ bots?",
    #         "exit"
    #     ]
    # )

    # # ── TEST 2: License Creation (Multi-turn) ────────────────
    # # User provides info slowly, one or two fields at a time
    # run_test_scenario(
    #     name="License Creation (Multi-turn with Missing Info)",
    #     user_id="test_license_user",
    #     inputs=[
    #         "Hi, I want to get a license for DSQ V2",
    #         "My MT5 ID is 12345678",
    #         "Name is Rahul Sharma",
    #         "I use Zerodha",
    #         "It's a Live account",
    #         "exit"
    #     ]
    # )

    # # ── TEST 3: License Creation (Partial dump + fix) ────────
    # # User gives some info, misses one, then provides it
    # run_test_scenario(
    #     name="License Creation (Partial then Complete)",
    #     user_id="test_license_user_2",
    #     inputs=[
    #         "I need a license. MT5 ID 87654321, broker is IC Markets",
    #         "Name is Priya and it's a Demo account",
    #         "exit"
    #     ]
    # )

    # # ── TEST 4: Setup Help ───────────────────────────────────
    # run_test_scenario(
    #     name="Setup Instructions",
    #     user_id="test_setup_user",
    #     inputs=[
    #         "How do I install DSQ V3?",
    #         "exit"
    #     ]
    # )

    # ── INTERACTIVE MODE ─────────────────────────────────────
    print("\n" + "=" * 70)
    print("  INTERACTIVE LIVE TEST MODE")
    print("=" * 70)
    print("Type your messages below. The agent will respond live.")
    print("Type \"exit\" to end the conversation.")
    print("Type \"quit\" to stop the program.")
    print("=" * 70)

    user_id = "interactive_user"
    memory.clear(user_id)
    memory.set_agent(user_id, True)
    print(f"\n🤖 Agent: {enter_agent_mode(user_id)}")

    while True:
        try:
            user_input = input("\n👤 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ["quit", "/quit", "/q"]:
            print("\nGoodbye!")
            break

        try:
            response = run_agent(user_input, user_id)
            print(f"🤖 Agent: {response}")
        except Exception as e:
            print(f"❌ ERROR: {e}")