from telegram import Update
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import logging
import json
import base64
from datetime import datetime, timedelta
import httpx

from config import GITHUB_TOKEN, GITHUB_API_URL_V1, BRANCH

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== STATES ====================
ASK_MT5, ASK_NAME, ASK_BROKER, ASK_ACCOUNT_TYPE = range(4)

# ==================== HELPER ====================
def get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("lang", "en")

# ==================== GITHUB UPDATE LOGIC ====================
async def update_github_licence(mt5_id: str, name: str, broker: str, account_type: str) -> dict:
    """Fetch the JSON file, add user, and commit back to GitHub."""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        # 1. Get file metadata and content
        resp = await client.get(GITHUB_API_URL_V1, headers=headers, params={"ref": BRANCH})
        resp.raise_for_status()
        meta = resp.json()
        sha = meta["sha"]
        content_b64 = meta["content"].replace("\n", "")
        content_bytes = base64.b64decode(content_b64)
        data = json.loads(content_bytes)

        # 2. Add user (check for duplicate)
        users_list = data.get("users", [])
        if any(u.get("user_id") == mt5_id for u in users_list):
            raise ValueError(f"MT5 ID {mt5_id} already exists.")

        valid_upto = (datetime.utcnow() + timedelta(days=90)).strftime("%d-%m-%Y")
        new_user = {
            "user_id": mt5_id,
            "server_name": "unknown",
            "broker": broker.lower(),
            "name": name,
            "account_type": account_type,   # "demo" or "real"
            "valid_upto": valid_upto
        }
        users_list.append(new_user)
        data["users"] = users_list

        # 3. Commit the updated file
        new_content_str = json.dumps(data, indent=2)
        new_content_b64 = base64.b64encode(new_content_str.encode()).decode()
        payload = {
            "message": f"Add user {mt5_id} ({name})",
            "content": new_content_b64,
            "sha": sha,
            "branch": BRANCH
        }
        resp = await client.put(GITHUB_API_URL_V1, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()

# ==================== TIMEOUT HANDLER ====================
async def timeout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    context.user_data.pop("licence_mt5", None)
    context.user_data.pop("licence_name", None)
    context.user_data.pop("licence_broker", None)
    if lang == "hi":
        msg = "⌛ आपने बहुत अधिक समय लिया। कृपया /get_licence_v1 से पुनः प्रारंभ करें।"
    else:
        msg = "⌛ You took too long. Please start again with /get_licence_v1."
    if update and update.effective_chat:
        await update.effective_chat.send_message(msg)
    return ConversationHandler.END

# ==================== FALLBACK FOR ANY COMMAND ====================
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    context.user_data.pop("licence_mt5", None)
    context.user_data.pop("licence_name", None)
    context.user_data.pop("licence_broker", None)
    if lang == "hi":
        msg = "❌ प्रक्रिया रद्द कर दी गई। /get_licence_v1 से पुनः प्रारंभ करें।"
    else:
        msg = "❌ Process cancelled. Use /get_licence_v1 to start again."
    await update.message.reply_text(msg)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    context.user_data.pop("licence_mt5", None)
    context.user_data.pop("licence_name", None)
    context.user_data.pop("licence_broker", None)
    msg = "❌ लाइसेंस जमा करना रद्द कर दिया गया।" if lang == "hi" else "❌ Licence submission cancelled."
    await update.message.reply_text(msg)
    return ConversationHandler.END

# ==================== STEP HANDLERS ====================
async def licence_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    if lang == "hi":
        msg = (
            "📋 आइए आपका लाइसेंस एक्टिवेट करें!\n\n"
            "✨ <b>सुझाव:</b> पहले डेमो अकाउंट का उपयोग करें, फिर रियल अकाउंट का।\n"
            "🔓 लाइसेंस किसी भी संख्या में खातों के लिए बनाया जा सकता है – चिंता न करें, यह हमेशा मुफ्त है।\n\n"
            "सबसे पहले अपनी <b>MT5 आईडी</b> भेजें (उदा. 12345678):"
        )
    else:
        msg = (
            "📋 Let's activate your licence!\n\n"
            "✨ <b>Tip:</b> Use a Demo account first, then a Real account.\n"
            "🔓 Licence can be created for any number of accounts – don't worry, it's always free.\n\n"
            "First, send your <b>MT5 ID</b> (e.g., 12345678):"
        )
    await update.message.reply_text(msg, parse_mode="HTML")
    return ASK_MT5


async def ask_mt5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["licence_mt5"] = update.message.text.strip()
    lang = get_lang(context)
    if lang == "hi":
        msg = "अब अपना <b>पूरा नाम</b> भेजें (उदा. John Doe):"
    else:
        msg = "Now send your <b>Full Name</b> (e.g., John Doe):"
    await update.message.reply_text(msg, parse_mode="HTML")
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["licence_name"] = update.message.text.strip()
    lang = get_lang(context)
    if lang == "hi":
        msg = "अब अपना <b>ब्रोकर</b> भेजें (उदा. XM, Vantage, Roboforex, Exness):"
    else:
        msg = "Now send your <b>Broker</b> (e.g., XM, Vantage, Roboforex, Exness):"
    await update.message.reply_text(msg, parse_mode="HTML")
    return ASK_BROKER

async def ask_broker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["licence_broker"] = update.message.text.strip()
    lang = get_lang(context)
    if lang == "hi":
        msg = "अंत में, यह <b>डेमो</b> या <b>रियल</b> अकाउंट है?\nकृपया <b>Demo</b> या <b>Real</b> टाइप करें।"
    else:
        msg = "Finally, is this a <b>Demo</b> or <b>Real</b> account?\nPlease type <b>Demo</b> or <b>Real</b>."
    await update.message.reply_text(msg, parse_mode="HTML")
    return ASK_ACCOUNT_TYPE

async def ask_account_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    account_type = update.message.text.strip().lower()
    if account_type not in ("demo", "real"):
        lang = get_lang(context)
        if lang == "hi":
            msg = "❌ कृपया केवल <b>Demo</b> या <b>Real</b> टाइप करें।"
        else:
            msg = "❌ Please type only <b>Demo</b> or <b>Real</b>."
        await update.message.reply_text(msg, parse_mode="HTML")
        return ASK_ACCOUNT_TYPE

    mt5 = context.user_data.pop("licence_mt5")
    name = context.user_data.pop("licence_name")
    broker = context.user_data.pop("licence_broker")
    lang = get_lang(context)

    # --- Personalised progress message using Telegram user's first name ---
    tg_first = update.effective_user.first_name if update.effective_user else "there"

    if lang == "hi":
        progress_text = f"⏳ {tg_first} जी, आपका लाइसेंस अपडेट हो रहा है... कृपया प्रतीक्षा करें।"
    else:
        progress_text = f"⏳ {tg_first}, your licence is being updated... Please wait."

    progress_msg = await update.message.reply_text(progress_text)

    try:
        await update_github_licence(mt5, name, broker, account_type)

        # Success message (still uses the licence name)
        if lang == "hi":
            final_msg = (
                f"✅ धन्यवाद, {name}! आपके बॉट के लिए लाइसेंस बनाया गया है।\n"
                f"MT5 आईडी: {mt5}\n"
                f"नाम: {name}\n"
                f"ब्रोकर: {broker}\n"
                f"खाता प्रकार: {account_type.capitalize()}\n\n"
                "⚙️ <b>लाइसेंस तभी काम करेगा जब:</b>\n"
                "MetaTrader में, Tools → Options → Expert Advisors:\n"
                "✅ Allow Algorithmic Trading\n"
                "✅ Allow Web Request for listed URL → जोड़ें: https://raw.githubusercontent.com\n\n"
                "💡 <b>टिप्स:</b>\n"
                "1. जब बाजार आपकी ग्रिड पोजीशन के विपरीत दिशा में तेजी से चल रहा हो तो सावधानी से ट्रेड करें। "
                "MT5 में Ctrl+E दबाकर एल्गो बंद करें और सभी पोजीशन मैन्युअली बंद करें।\n"
                "2. जोखिम के बारे में अधिक जानने के लिए /risk_v1 का उपयोग करें।"
            )
        else:
            final_msg = (
                f"✅ Thank you, {name}! Your licence has been created for your bot.\n"
                f"MT5 ID: {mt5}\n"
                f"Name: {name}\n"
                f"Broker: {broker}\n"
                f"Account: {account_type.capitalize()}\n\n"
                "⚙️ <b>Licence will work only if:</b>\n"
                "In MetaTrader, go to Tools → Options → Expert Advisors:\n"
                "✅ Allow Algorithmic Trading\n"
                "✅ Allow Web Request for listed URL → Add: https://raw.githubusercontent.com\n\n"
                "💡 <b>Tips:</b>\n"
                "1. Trade carefully when market is moving in one direction against your grid position. "
                "You should stop the algo at MT5 (Ctrl+E) and close all positions manually.\n"
                "2. Know more about risk at /risk_v1"
            )

        await progress_msg.edit_text(final_msg, parse_mode="HTML", disable_web_page_preview=True)

    except ValueError as e:
        logger.warning(str(e))
        if lang == "hi":
            error_msg = f"❌ एमटी5 आईडी {mt5} पहले से मौजूद है। कृपया नई आईडी के साथ /get_licence_v1 से प्रयास करें।"
        else:
            error_msg = f"❌ MT5 ID {mt5} already exists. Please try again with a different ID using /get_licence_v1."
        await progress_msg.edit_text(error_msg)

    except Exception as e:
        logger.error(f"GitHub update failed: {e}")
        if lang == "hi":
            error_msg = "❌ सर्वर त्रुटि। कृपया बाद में पुनः प्रयास करें।"
        else:
            error_msg = "❌ Server error. Please try again later."
        await progress_msg.edit_text(error_msg)

    return ConversationHandler.END



# ==================== BUILD HANDLER ====================
licence_conv_v1 = ConversationHandler(
    entry_points=[CommandHandler("get_licence_v1", licence_start)],
    states={
        ASK_MT5: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_mt5)],
        ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
        ASK_BROKER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_broker)],
        ASK_ACCOUNT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_account_type)],
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        MessageHandler(filters.COMMAND, cancel_command),
    ],
    conversation_timeout=60,
)