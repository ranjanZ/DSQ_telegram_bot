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

from config import GITHUB_TOKEN, GITHUB_API_URL_V2, BRANCH

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# States
SHOW_ACCOUNT_INFO, ASK_MT5, ASK_NAME, ASK_BROKER, ASK_ACCOUNT_TYPE = range(5)

def get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("lang", "en")

# ==================== GITHUB UPDATE ====================
async def update_github_licence_v2(mt5_id: str, name: str, broker: str, account_type: str) -> dict:
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(GITHUB_API_URL_V2, headers=headers, params={"ref": BRANCH})
        resp.raise_for_status()
        meta = resp.json()
        sha = meta["sha"]
        content_b64 = meta["content"].replace("\n", "")
        content_bytes = base64.b64decode(content_b64)
        data = json.loads(content_bytes)

        users_list = data.get("users", [])
        if any(u.get("user_id") == mt5_id for u in users_list):
            raise ValueError(f"MT5 ID {mt5_id} already exists.")

        valid_upto = (datetime.utcnow() + timedelta(days=1)).strftime("%d-%m-%Y")
        new_user = {
            "user_id": mt5_id,
            "server_name": "unknown",
            "broker": broker.lower(),
            "name": name,
            "account_type": account_type,
            "valid_upto": valid_upto
        }
        users_list.append(new_user)
        data["users"] = users_list

        new_content_str = json.dumps(data, indent=2)
        new_content_b64 = base64.b64encode(new_content_str.encode()).decode()
        payload = {
            "message": f"Add V2 user {mt5_id} ({name})",
            "content": new_content_b64,
            "sha": sha,
            "branch": BRANCH
        }
        resp = await client.put(GITHUB_API_URL_V2, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()

# ==================== FALLBACKS & TIMEOUT ====================
async def timeout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    for key in ("licence_mt5", "licence_name", "licence_broker"):
        context.user_data.pop(key, None)
    if lang == "hi":
        msg = "⌛ आपने बहुत अधिक समय लिया। कृपया /get_licence_v2 से पुनः प्रारंभ करें।"
    else:
        msg = "⌛ You took too long. Please start again with /get_licence_v2."
    if update and update.effective_chat:
        await update.effective_chat.send_message(msg)
    return ConversationHandler.END

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    for key in ("licence_mt5", "licence_name", "licence_broker"):
        context.user_data.pop(key, None)
    if lang == "hi":
        msg = "❌ प्रक्रिया रद्द कर दी गई। /get_licence_v2 से पुनः प्रारंभ करें।"
    else:
        msg = "❌ Process cancelled. Use /get_licence_v2 to start again."
    await update.message.reply_text(msg)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    for key in ("licence_mt5", "licence_name", "licence_broker"):
        context.user_data.pop(key, None)
    msg = "❌ लाइसेंस जमा करना रद्द कर दिया गया।" if lang == "hi" else "❌ Licence submission cancelled."
    await update.message.reply_text(msg)
    return ConversationHandler.END

# ==================== STEP 1: ACCOUNT INFO + CONFIRMATION ====================
async def licence_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        lang = get_lang(context)
        if lang == "hi":
            msg = "कृपया लाइसेंस प्रक्रिया जारी रखने के लिए मुझे [telegram bot] निजी संदेश भेजें।"
        else:
            msg = "Please send me [telegram bot] a private message to continue the licence process."
        await update.message.reply_text(msg)
        return ConversationHandler.END

    lang = get_lang(context)
    if lang == "hi":
        msg = (
            "📋 <b>V2 लाइसेंस सक्रियण – चरण 1</b>\n\n"
            "यदि आपके पास खाता नहीं है, तो आप नीचे दिए गए लिंक से खाता खोल सकते हैं:\n\n"
            "🔹 <a href='https://vantagemarkets.com/open-live-account/?affid=MjMxNDEyNzM=&invitecode=VcM6U1DW'>Vantage खाता खोलें</a>\n"
            "🔹 <a href='https://my.roboforex.com/en/?a=zrfhm'>Roboforex खाता खोलें</a>\n"
            "🔹 <a href='https://affs.click/mvjlf'>XM खाता खोलें</a>\n"
            "🔹 <a href='https://one.exnessonelink.com/a/c_niibgmkreg'>Exness खाता खोलें</a>\n\n"
            "यदि आपके पास पहले से XM / Vantage / Roboforex / Exness खाता है, तो कृपया पार्टनर कोड जोड़ें:\n"
            "▪ Vantage Partner Code: <code>VcM6U1DW</code>\n"
            "▪ Roboforex Partner Code: <code>zrfhm</code>\n"
            "▪ XM Partner Code: <code>4299V</code> — <a href='https://youtu.be/XoasAO63nfc'>गाइड वीडियो</a>\n"
            "▪ Exness Partner Code: <code>c_niibgmkreg</code>\n\n"
            "⚠️ क्या आपने पार्टनर कोड जोड़ दिया है?\n"
            "यदि हाँ, तो <b>Yes</b> या <b>हाँ</b> भेजें।\n"
            "/cancel से रद्द करें।"
        )
    else:
        msg = (
            "📋 <b>V2 Licence Activation – Step 1</b>\n\n"
            "If you don't have an account, you can open one from the links below:\n\n"
            "🔹 <a href='https://vantagemarkets.com/open-live-account/?affid=MjMxNDEyNzM=&invitecode=VcM6U1DW'>Open Vantage Account</a>\n"
            "🔹 <a href='https://my.roboforex.com/en/?a=zrfhm'>Open Roboforex Account</a>\n"
            "🔹 <a href='https://affs.click/mvjlf'>Open XM Account</a>\n"
            "🔹 <a href='https://one.exnessonelink.com/a/c_niibgmkreg'>Open Exness Account</a>\n\n"
            "If you already have an XM / Vantage / Roboforex / Exness account, add the partner code:\n"
            "▪ Vantage Partner Code: <code>VcM6U1DW</code>\n"
            "▪ Roboforex Partner Code: <code>zrfhm</code>\n"
            "▪ XM Partner Code: <code>4299V</code> — <a href='https://youtu.be/XoasAO63nfc'>Guide Video</a>\n"
            "▪ Exness Partner Code: <code>c_niibgmkreg</code>\n\n"
            "⚠️ Have you added the partner code?\n"
            "If yes, send <b>Yes</b> (or <b>yes</b>).\n"
            "Send /cancel to abort."
        )
    await update.message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)
    return SHOW_ACCOUNT_INFO

async def confirm_partner_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    answer = update.message.text.strip().lower()
    positive_answers = {"yes", "y", "haan", "हाँ", "हां"}
    if answer in positive_answers:
        if lang == "hi":
            msg = "✅ धन्यवाद! अब <b>चरण 2:</b> अपनी <b>MT5 आईडी</b> भेजें (उदा. 12345678):"
        else:
            msg = "✅ Great! <b>Step 2:</b> Now send your <b>MT5 ID</b> (e.g., 12345678):"
        await update.message.reply_text(msg, parse_mode="HTML")
        return ASK_MT5
    else:
        if lang == "hi":
            msg = "❌ कृपया <b>Yes</b> या <b>हाँ</b> भेजें, या /cancel से रद्द करें।"
        else:
            msg = "❌ Please send <b>Yes</b> to confirm, or /cancel to abort."
        await update.message.reply_text(msg, parse_mode="HTML")
        return SHOW_ACCOUNT_INFO

# ==================== STEP 2: COLLECT MT5, NAME, BROKER, TYPE ====================
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

    tg_first = update.effective_user.first_name if update.effective_user else "there"
    if lang == "hi":
        progress_text = f"⏳ {tg_first} जी, आपका V2 लाइसेंस अपडेट हो रहा है... कृपया प्रतीक्षा करें।"
    else:
        progress_text = f"⏳ {tg_first}, your V2 licence is being updated... Please wait."
    progress_msg = await update.message.reply_text(progress_text)

    try:
        await update_github_licence_v2(mt5, name, broker, account_type)
        if lang == "hi":
            final_msg = (
                f"✅ धन्यवाद, {name}! आपके V2 बॉट के लिए लाइसेंस बनाया गया है।\n"
                f"MT5 आईडी: {mt5}\nनाम: {name}\nब्रोकर: {broker}\nखाता: {account_type.capitalize()}\n\n"
                "⚙️ <b>लाइसेंस तभी काम करेगा जब:</b>\n"
                "MetaTrader में, Tools → Options → Expert Advisors:\n"
                "✅ Allow Algorithmic Trading\n"
                "✅ Allow Web Request for listed URL → जोड़ें: https://raw.githubusercontent.com\n\n"
                "💡 <b>टिप्स:</b>\n"
                "1. जब बाजार विपरीत दिशा में जाए तो Ctrl+E से बॉट रोकें और पोजीशन मैन्युअली बंद करें।\n"
                "2. पूरी जोखिम जानकारी /risk_v2 पर देखें।"
            )
        else:
            final_msg = (
                f"✅ Thank you, {name}! Your V2 licence has been created for your bot.\n"
                f"MT5 ID: {mt5}\nName: {name}\nBroker: {broker}\nAccount: {account_type.capitalize()}\n\n"
                "⚙️ <b>Licence will work only if:</b>\n"
                "In MetaTrader, go to Tools → Options → Expert Advisors:\n"
                "✅ Allow Algorithmic Trading\n"
                "✅ Allow Web Request for listed URL → Add: https://raw.githubusercontent.com\n\n"
                "💡 <b>Tips:</b>\n"
                "1. When market moves against your grid, press Ctrl+E to stop the bot and close positions manually.\n"
                "2. See full risk info at /risk_v2"
            )
        await progress_msg.edit_text(final_msg, parse_mode="HTML", disable_web_page_preview=True)

    except ValueError as e:
        logger.warning(str(e))
        if lang == "hi":
            error_msg = f"❌ एमटी5 आईडी {mt5} पहले से मौजूद है। कृपया नई आईडी के साथ /get_licence_v2 से प्रयास करें।"
        else:
            error_msg = f"❌ MT5 ID {mt5} already exists. Please try again with a different ID using /get_licence_v2."
        await progress_msg.edit_text(error_msg)

    except Exception as e:
        logger.error(f"GitHub update failed: {e}")
        if lang == "hi":
            error_msg = "❌ सर्वर त्रुटि। कृपया बाद में पुनः प्रयास करें।"
        else:
            error_msg = "❌ Server error. Please try again later."
        await progress_msg.edit_text(error_msg)

    return ConversationHandler.END

# ==================== BUILD CONVERSATION HANDLER ====================
licence_conv_v2 = ConversationHandler(
    entry_points=[CommandHandler("get_licence_v2", licence_start)],
    states={
        SHOW_ACCOUNT_INFO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_partner_code)
        ],
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