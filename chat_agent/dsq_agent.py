"""
Dalal Street Quants - Robust Conversational Agent (Gemma2:2b)
Keyword-based intent + simple LLM entity extraction.
Handles: License creation (multi-turn), Setup help, General queries.
"""

import os
import json
import base64
import re
import requests
from typing import TypedDict, Annotated, Sequence, Literal
from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from datetime import datetime, timedelta

# Import your existing config
from config import *

# ─── Configuration ─────────────────────────────────────────────
OLLAMA_MODEL = "gemma2:2b"

llm = ChatOllama(model=OLLAMA_MODEL, temperature=0.1)

# Map version string to config variables
VERSION_CONFIG = {
    "v1": {"file_path": FILE_PATH_V1, "api_url": GITHUB_API_URL_V1},
    "v2": {"file_path": FILE_PATH_V2, "api_url": GITHUB_API_URL_V2},
    "v3": {"file_path": FILE_PATH_V3, "api_url": GITHUB_API_URL_V3},
    "v4": {"file_path": FILE_PATH_V4, "api_url": GITHUB_API_URL_V4},
}

# ─── State ─────────────────────────────────────────────────────
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "add_messages"]
    intent: Literal["license", "setup", "general", "exit", "unknown"]
    collected: dict
    missing: list
    action_result: dict
    response: str
    done: bool


# ─── Helper: Keyword Intent Detection ──────────────────────────
EXIT_KEYWORDS = ["exit", "quit", "menu", "stop", "bye", "goodbye", "/start"]
LICENSE_KEYWORDS = ["license", "licence", "licens", "key", "generate key", "get key", 
                   "want license", "need license", "create license", "license key",
                   "activation", "activate"]
SETUP_KEYWORDS = ["setup", "install", "how do i", "how to", "setting up", "attach",
                 "download", "configure", "put the bot", "run the bot", "use the bot"]

def _detect_intent(last_msg: str, prev_messages: list) -> str:
    """Fast keyword-based intent detection. No LLM needed."""
    msg = last_msg.lower().strip()

    # Exit
    if any(k in msg for k in EXIT_KEYWORDS):
        return "exit"

    # License
    if any(k in msg for k in LICENSE_KEYWORDS):
        return "license"

    # Setup
    if any(k in msg for k in SETUP_KEYWORDS):
        return "setup"

    # Number selection from previous menu (e.g. user types "1" or "2")
    if msg in ["1", "2", "3"] and prev_messages:
        for prev in reversed(prev_messages):
            if isinstance(prev, AIMessage):
                content = prev.content
                if "1." in content and "license" in content.lower():
                    if msg == "1":
                        return "license"
                    elif msg == "2":
                        return "setup"
                    elif msg == "3":
                        return "general"
                break

    # Default to general (let LLM handle it)
    return "general"


# ─── Helper: Simple Entity Extraction ──────────────────────────
ENTITY_PROMPT = """Extract information from the user's message.
Return ONLY a JSON object with found fields. No explanation. No markdown.

Fields to look for:
- metatrader_id: MetaTrader account number (digits only)
- name: person's full name
- broker: broker company name
- server_name: MetaTrader server name (e.g. "MetaQuotes-Demo", "ICMarkets-Live")
- version: "v1", "v2", "v3", or "v4" (or "1","2","3","4")

Example output: {"name":"Rahul","broker":"Zerodha","version":"v2"}
If nothing found, output: {}
"""

def _extract_entities(messages: Sequence[BaseMessage]) -> dict:
    """Use LLM to extract entities. Very short prompt for 2B model."""
    msgs = [SystemMessage(content=ENTITY_PROMPT)] + list(messages[-2:])

    try:
        raw = llm.invoke(msgs).content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        if not raw or raw[0] != "{":
            match = re.search(r'\{.*?\}', raw, re.DOTALL)
            if match:
                raw = match.group(0)
            else:
                return {}
        entities = json.loads(raw)
        return entities if isinstance(entities, dict) else {}
    except Exception:
        return {}


# ─── Node 1: Understand ────────────────────────────────────────
def understand(state: AgentState) -> AgentState:
    """Understand user intent and extract entities."""

    messages = list(state["messages"])
    last_msg = messages[-1].content if messages else ""
    prev_messages = messages[:-1]

    # Step 1: Detect intent via keywords (reliable)
    intent = _detect_intent(last_msg, prev_messages)

    # Step 2: Merge previous collected data
    collected = state.get("collected", {}).copy()

    # Step 3: Extract new entities via LLM (only for license/setup)
    if intent in ["license", "setup"]:
        new_entities = _extract_entities(messages)
        # Normalize version
        if "version" in new_entities:
            v = str(new_entities["version"]).lower().replace(" ", "")
            if "v1" in v or v == "1":
                new_entities["version"] = "v1"
            elif "v2" in v or v == "2":
                new_entities["version"] = "v2"
            elif "v3" in v or v == "3":
                new_entities["version"] = "v3"
            elif "v4" in v or v == "4":
                new_entities["version"] = "v4"
        collected.update(new_entities)

    # Step 4: Compute missing fields in code
    missing = []
    if intent == "license":
        required = ["metatrader_id", "name", "broker", "server_name", "version"]
        for field in required:
            if field not in collected or not str(collected[field]).strip():
                missing.append(field)
    elif intent == "setup":
        if "version" not in collected or not collected["version"]:
            missing.append("version")

    return {
        **state,
        "intent": intent,
        "collected": collected,
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
                "metatrader_id": "your MetaTrader 5 Account ID",
                "name": "your full name",
                "broker": "your broker's name", 
                "server_name": "your MetaTrader server name (e.g. MetaQuotes-Demo, ICMarkets-Live)",
                "version": "which bot version (V1, V2, V3, or V4)"
            }
            missing_labels = [field_labels.get(f, f) for f in missing]
            if len(missing_labels) == 1:
                question = f"To create your license, I still need {missing_labels[0]}. Could you please provide that?"
            else:
                question = (
                    "To create your license, I need the following information:\n"
                    + "\n".join(f"• {label}" for label in missing_labels)
                    + "\n\nPlease provide these details and I'll create your license right away."
                )
            result = {"type": "ask", "data": {"question": question}}
        else:
            success, msg = _create_license_on_github(collected)
            if success:
                version = collected.get("version", "v2").lower()
                result = {
                    "type": "license_created",
                    "data": {
                        "message": msg,
                        "name": collected["name"],
                        "metatrader_id": collected["metatrader_id"],
                        "broker": collected["broker"],
                        "version": version.upper()
                    }
                }
            else:
                result = {
                    "type": "error",
                    "data": {"message": msg}
                }

    # ── SETUP ──
    elif intent == "setup":
        if missing:
            result = {
                "type": "ask",
                "data": {"question": "Which version do you need setup help for? (V1, V2, V3, or V4)"}
            }
        else:
            version = collected.get("version", "v2").lower()
            if version not in ["v1", "v2", "v3", "v4"]:
                version = "v2"
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
                "question": "I can help you with:\n1. Creating a license (V1, V2, V3, or V4)\n2. Bot setup instructions\n3. General questions about our bots\n\nWhat would you like to do?"
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
        "🆔 MetaTrader ID: {metatrader_id}\n"
        "🏢 Broker: {broker}\n"
        "📦 Version: {version}\n\n"
        "{message}"
    ),
    "error": "❌ {message}",
    "setup_instructions": (
        "📘 **Setup Instructions for DSQ {version}**\n\n"
        "{instructions}\n\n"
        "Need a license next? Just say 'I want a license'!"
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
    """
    Append user entry to the version-specific JSON file on GitHub.
    Checks if metatrader_id already exists — if yes, returns duplicate message.
    Uses FILE_PATH_V{1,2,3,4} and GITHUB_API_URL_V{1,2,3,4} from config.
    Returns (success, message).
    """

    if not GITHUB_TOKEN:
        return False, "GitHub token not configured."

    version = collected.get("version", "v2").lower()
    if version not in VERSION_CONFIG:
        version = "v2"

    cfg = VERSION_CONFIG[version]
    api_url = cfg["api_url"]
    file_path = cfg["file_path"]

    metatrader_id = str(collected["metatrader_id"])
    name = collected["name"]
    broker = collected["broker"]
    server_name = collected.get("server_name", "")

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Try to fetch existing file
    sha = None
    existing_licenses = []

    get_resp = requests.get(api_url, headers=headers)
    if get_resp.status_code == 200:
        data = get_resp.json()
        sha = data.get("sha")
        try:
            content_b64 = data.get("content", "")
            content_json = base64.b64decode(content_b64.replace("\n", "")).decode("utf-8")
            existing_licenses = json.loads(content_json)
            if not isinstance(existing_licenses, list):
                existing_licenses = [existing_licenses] if existing_licenses else []
        except Exception:
            existing_licenses = []

    # ─── CHECK FOR DUPLICATE ───────────────────────────────────
    for entry in existing_licenses:
        if str(entry.get("metatrader_id", "")) == metatrader_id:
            return False, f"License already exists with this MetaTrader account ID ({metatrader_id})."

    # Valid upto = today + 6 months
    valid_upto = (datetime.now() + timedelta(days=180)).strftime("%d-%m-%Y")

    # Verified field based on version
    if version in ["v1", "v2"]:
        verified = "True"
        success_msg = "You are now ready to use the bot. 🚀"
    else:
        verified = "False"
        success_msg = "Please wait for verification. After verification you can use the bot. ⏳"

    # New license entry
    new_entry = {
        "metatrader_id": metatrader_id,
        "server_name": server_name,
        "broker": broker,
        "name": name,
        "Verified": verified,
        "valid_upto": valid_upto
    }

    # Append new entry
    existing_licenses.append(new_entry)

    # Encode back to base64
    new_content = json.dumps(existing_licenses, indent=2)
    new_content_b64 = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")

    payload = {
        "message": f"license: add {name} ({metatrader_id}) to {file_path}",
        "content": new_content_b64,
        "branch": BRANCH
    }
    if sha:
        payload["sha"] = sha

    put_resp = requests.put(api_url, headers=headers, json=payload)

    if put_resp.status_code in [200, 201]:
        return True, success_msg
    return False, "Failed to push license to GitHub. Please try again."


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
    Run: python dsq_agent.py
    Requirements: Ollama with gemma2:2b, config.py in same folder
    """

    def run_test_scenario(name: str, user_id: str, inputs: list[str]):
        print("\n" + "=" * 70)
        print(f"  TEST SCENARIO: {name}")
        print("=" * 70)

        memory.clear(user_id)
        memory.set_agent(user_id, True)

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
    #         "hi",
    #         "What is the risk management strategy in DSQ bots?",
    #         "exit"
    #     ]
    # )

    # # ── TEST 2: Setup Help ───────────────────────────────────
    # run_test_scenario(
    #     name="Setup Instructions",
    #     user_id="test_setup_user",
    #     inputs=[
    #         "How do I install DSQ V3?",
    #         "exit"
    #     ]
    # )

    # # ── TEST 3: V1 License (Verified=True, ready msg) ────────
    # run_test_scenario(
    #     name="V1 License Creation (Auto-Verified)",
    #     user_id="test_v1_license",
    #     inputs=[
    #         "I want a V1 license. MT5 ID 12345678, name Rahul Sharma, broker Zerodha, server MetaQuotes-Demo",
    #         "exit"
    #     ]
    # )

    # # ── TEST 4: V2 License (Verified=True, ready msg) ────────
    # run_test_scenario(
    #     name="V2 License Creation (Auto-Verified)",
    #     user_id="test_v2_license",
    #     inputs=[
    #         "Create license for V2. MT5 87654321, name Priya, broker IC Markets, server ICMarkets-Live",
    #         "exit"
    #     ]
    # )

    # # ── TEST 5: V3 License (Verified=False, wait msg) ────────
    # run_test_scenario(
    #     name="V3 License Creation (Wait for Verification)",
    #     user_id="test_v3_license",
    #     inputs=[
    #         "I need a V3 license. MT5 11112222, name Alex, broker XM, server XMGlobal-Demo",
    #         "exit"
    #     ]
    # )

    # # ── TEST 6: V4 License (Verified=False, wait msg) ────────
    # run_test_scenario(
    #     name="V4 License Creation (Wait for Verification)",
    #     user_id="test_v4_license",
    #     inputs=[
    #         "License for V4. MT5 99998888, name Sam, broker FBS, server FBS-Real",
    #         "exit"
    #     ]
    # )

    # # ── TEST 7: Duplicate License Check ──────────────────────
    # run_test_scenario(
    #     name="Duplicate License Check",
    #     user_id="test_duplicate",
    #     inputs=[
    #         "I want a V2 license. MT5 ID 12345678, name Rahul Sharma, broker Zerodha, server MetaQuotes-Demo",
    #         "exit"
    #     ]
    # )

    # # ── TEST 8: License (partial, then complete) ─────────────
    # run_test_scenario(
    #     name="License Creation (Partial → Complete)",
    #     user_id="test_license_partial",
    #     inputs=[
    #         "I need a license",
    #         "V2",
    #         "MT5 ID 55556666, broker Exness",
    #         "Name is John, server Exness-MT5Trial",
    #         "exit"
    #     ]
    # )

    # ── INTERACTIVE MODE ─────────────────────────────────────
    print("\n" + "=" * 70)
    print("  INTERACTIVE LIVE TEST MODE")
    print("=" * 70)
    print("Type your messages. The agent responds live.")
    print('Type "exit" to end conversation. Type "quit" to stop.')
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