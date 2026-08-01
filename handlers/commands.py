from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import logging

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

DOWNLOAD_URL = "https://github.com/ranjanZ/ranjanZ.github.io/raw/refs/heads/master/blog/dalal_street_quants/DSQ_EA/dsq_v1.ex5"

def get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("lang", "en")

# ==================== REGULAR COMMANDS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    if lang == "hi":
        msg = (
            "👋 आपका स्वागत है! [अभी सब कुछ फ्री है]\n\n"
            "/start – यह मेनू दिखाएं\n"
            "/change_lang – भाषा बदलें (English ↔ हिंदी)\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🤖 <b>Bot DSQ V1</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "/get_dsq_v1 – ग्रिड बॉट V1 डाउनलोड करें\n"
            "/get_licence_v1 – लाइसेंस फॉर्म\n"
            "/get_setup_instruction_v1 – सेटअप निर्देश\n"
            "/risk_v1 – जोखिम जानकारी\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🤖 <b>Bot DSQ V2</b> (जल्द आ रहा है)\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "/get_dsq_v2 – ग्रिड बॉट V2 डाउनलोड करें\n"
            "/get_licence_v2 – लाइसेंस फॉर्म\n"
            "/get_setup_instruction_v2 – सेटअप निर्देश\n"
            "/risk_v2 – जोखिम जानकारी"
        )
    else:
        msg = (
            "👋 Welcome! [Everything is free for now]\n\n"
            "/start – Show this menu\n"
            "/change_lang – Toggle language (English ↔ हिंदी)\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🤖 <b>Bot DSQ V1</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "/get_dsq_v1 – Download Grid bot V1\n"
            "/get_licence_v1 – Licence form\n"
            "/get_setup_instruction_v1 – Setup instructions\n"
            "/risk_v1 – Risk information\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🤖 <b>Bot DSQ V2</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "/get_dsq_v2 – Download Grid bot V2\n"
            "/get_licence_v2 – Licence form\n"
            "/get_setup_instruction_v2 – Setup instructions\n"
            "/risk_v2 – Risk information"
        )
    await update.message.reply_text(msg, parse_mode="HTML")

async def change_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current = get_lang(context)
    new_lang = "hi" if current == "en" else "en"
    context.user_data["lang"] = new_lang
    msg = "✅ भाषा बदली गई: अब हिंदी।" if new_lang == "hi" else "✅ Language toggled: now English."
    await update.message.reply_text(msg)

async def get_dsq_v1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    if lang == "hi":
        label = "यहां क्लिक करके डाउनलोड करें"
        base = f"📦 ग्रिड बॉट V1 संस्करण डाउनलोड करें:\n<a href=\"{DOWNLOAD_URL}\">{label}</a>"
    else:
        label = "Click here to download"
        base = f"📦 Download Grid bot V1 version:\n<a href=\"{DOWNLOAD_URL}\">{label}</a>"
    await update.message.reply_text(base, parse_mode="HTML", disable_web_page_preview=True)

async def get_setup_instruction_v1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    if lang == "hi":
        msg = (
            "🛠️ <b>सेटअप गाइड (टेलीग्राम से)</b>\n\n"
            "1. <b>MT5 डाउनलोड करें और लॉगिन करें</b>\n"
            "आधिकारिक वेबसाइट metatrader5.com से MT5 डाउनलोड करें।\n"
            "अपने ब्रोकर के User ID, Password और Server से लॉगिन करें।\n\n"
            "2. <b>MetaTrader सेटिंग्स</b>\n"
            "Tools → Options → Expert Advisors:\n"
            "✅ Allow Algorithmic Trading\n"
            "✅ Allow Web Request for listed URL → जोड़ें: https://raw.githubusercontent.com\n\n"
            "3. <b>एल्गो बॉट डाउनलोड करें</b>\n"
            "/get_dsq_v1 का उपयोग करें, फिर डाउनलोड की गई फाइल पर डबल‑क्लिक करें → यह MetaTrader में जुड़ जाएगी।\n"
            "Navigator पैनल (दाईं ओर) में dsq_v1 को Expert Advisors के अंतर्गत देखें।\n\n"
            "4. <b>लाइसेंस एक्टिवेट करें</b>\n"
            "/get_licence_v1 का उपयोग करें।\n\n\n\n\n\n\n\n"
            "🌐 <b>DSQ वेबगाइड(पेज से सेटअप)</b>\n"
            "https://shorturl.at/YU5yw\n"
            "ऊपर दिए गए लिंक को खोलें, \"Free Bot Setup\" पर जाएं और अपने कंप्यूटर पर मुफ्त सेटअप के निर्देशों का पालन करें।\n\n"
            "📹 <b>निर्देश वीडियो</b>\n"
            "सेटअप निर्देश वीडियो: https://www.youtube.com/watch?v=AikfpXh4W4U\n"
            "जोखिम कम करने के लिए कौन सा अकाउंट इस्तेमाल करें: https://www.youtube.com/watch?v=gG-SbraJwiY"
        )
    else:
        msg = (
            "🛠️ <b>Setup Guide (from Telegram)</b>\n\n"
            "1. <b>Download MT5 &amp; Login</b>\n"
            "Download MT5 from the official website: metatrader5.com\n"
            "Login with your broker’s User ID, Password, and Server (MetaTrader 5).\n\n"
            "2. <b>MetaTrader Settings</b>\n"
            "In MetaTrader, go to Tools → Options → Expert Advisors:\n"
            "✅ Allow Algorithmic Trading\n"
            "✅ Allow Web Request for listed URL → Add: https://raw.githubusercontent.com\n\n"
            "3. <b>Download the Algo Bot (dsq_v1)</b>\n"
            "Use /get_dsq_v1, then double‑click the downloaded file → it will be added to MetaTrader.\n"
            "In the Navigator panel (right side), find dsq_v1 under Expert Advisors.\n\n"
            "4. <b>Activate your Bot Licence</b>\n"
            "Use /get_licence_v1\n\n\n\n\n\n\n\n"
            "🌐 <b>Setup Guide(from DSQ Web Page [This will be up after 13th of June. Get license directly from Telegram bot])</b>\n"
            "https://shorturl.at/YU5yw\n"
            "Open the link above, go to \"Free Bot Setup\" and follow the instructions to set up in your computer for free.\n\n"
            "📹 <b>Instruction Videos</b>\n"
            "Set up in instruction video: https://www.youtube.com/watch?v=AikfpXh4W4U\n"
            "Which account to use to minimize risk: https://www.youtube.com/watch?v=gG-SbraJwiY"
        )
    await update.message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)

async def risk_v1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    if lang == "hi":
        msg = (
            "<b>dsq_v1 बॉट मानदंड और जोखिम – ध्यान से पढ़ें</b>\n\n"
            "यदि आपके पास 10,000 INR (≈ 100 USD) है:\n"
            "→ आपको एक सेंट अकाउंट (USD नहीं) चाहिए।\n"
            "→ सेंट अकाउंट में 100 USD, 10,000 USC (ट्रेडिंग राशि) बन जाते हैं।\n"
            "→ न्यूनतम आवश्यकता: 100 USD जमा = 10,000 USC।\n\n"
            "💰 अपना अकाउंट प्रकार चुनें\n\n"
            "USD अकाउंट: कम से कम 10,000 USD की आवश्यकता → छोटी पूंजी के लिए नहीं।\n"
            "सेंट अकाउंट: कम से कम 100 USD की आवश्यकता → यह 10,000 INR के लिए है।\n\n"
            "⚠️ हमेशा पहले डेमो पर परीक्षण करें – वही ब्रोकर, वही सेंट अकाउंट प्रकार।\n"
            "dsq_v1 को तभी चलाएं जब बाजार साइडवेज़ हो।\n"
            "🆘 आपातकालीन स्टॉप: MetaTrader में Ctrl+E एक बार दबाएं। फिर सभी ट्रेड्स बंद करें।\n"
            "🔥 संगत सेंट अकाउंट [10,000 INR के लिए]\n\n"
            "<pre>"
            "ब्रोकर      | ✅ सेंट अकाउंट (काम करता है)   | ❌ USD अकाउंट (बहुत अधिक जोखिम)\n"
            "----------------------------------------------------------------------\n"
            "Vantage     | ✓ cent STP (1:2000)          | ✗ Normal STP\n"
            "XM          | ✓ Micro account (1:1000)     | ✗ Ultra Low / Standard\n"
            "Roboforex   | ✓ ProCent account (1:2000)   | ✗ Pro account\n"
            "Exness      | ✓ USC account               | ✗ USD account\n"
            "</pre>\n\n"
            "उदाहरण: 10,000 INR → 100 USD जमा → 10,000 USC मिलते हैं।\n\n"
            "───────\n"
            "<b>ℹ️ महत्वपूर्ण नोट:</b>\n"
            "• dsq_v1 <b>केवल गोल्ड (XAUUSD)</b> के लिए है।\n"
            "• FX या crypto पर न चलाएं।\n"
            "• <b>डिफ़ॉल्ट सेटिंग्स</b> का उपयोग करें।\n"
            "✅ कम जोखिम विकल्प: dsq_v2 या dsq_v3 (जल्द ही)।"
        )
    else:
        msg = (
            "<b>dsq_v1 Bot Criteria &amp; Risk – Read Carefully</b>\n\n"
            "If you have 10,000 INR (≈ 100 USD):\n"
            "→ You need a Cent Account.\n"
            "→ 100 USD becomes 10,000 USC.\n"
            "→ Minimum deposit: 100 USD.\n\n"
            "💰 Account type\n"
            "USD account: Needs $10,000 → too high.\n"
            "Cent account: Needs $100 → perfect for 10k INR.\n\n"
            "⚠️ Always test on Demo first.\n"
            "Run only sideways market.\n"
            "🆘 Emergency: Ctrl+E in MetaTrader.\n"
            "🔥 Compatible Cent Accounts:\n"
            "<pre>"
            "Broker      | ✅ Cent Account        | ❌ USD Account\n"
            "---------------------------------------------------\n"
            "Vantage     | ✓ cent STP (1:2000)   | ✗ Normal STP\n"
            "XM          | ✓ Micro account (1:1000)| ✗ Ultra Low / Standard\n"
            "Roboforex   | ✓ ProCent (1:2000)    | ✗ Pro\n"
            "Exness      | ✓ USC account         | ✗ USD\n"
            "</pre>\n\n"
            "Example: 10,000 INR → deposit $100 → get 10,000 USC.\n\n"
            "───────\n"
            "<b>ℹ️ Important:</b>\n"
            "• dsq_v1 is <b>only for Gold (XAUUSD)</b>.\n"
            "• Not for FX or crypto.\n"
            "• <b>Use default settings</b>.\n"
            "✅ Try dsq_v2/v3 later (hedging included)."
        )
    await update.message.reply_text(msg, parse_mode="HTML")

# ==================== V2 PLACEHOLDER HANDLERS ====================
async def get_dsq_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    DOWNLOAD_URL_V2 = "https://github.com/ranjanZ/DSQ_Page/raw/refs/heads/main/data/bots/dsq_v2.ex5"
    lang = get_lang(context)
    if lang == "hi":
        label = "यहां क्लिक करके डाउनलोड करें"
        msg = (
            f"📦 ग्रिड बॉट V2 संस्करण डाउनलोड करें:\n"
            f"<a href=\"{DOWNLOAD_URL_V2}\">{label}</a>\n\n"
            "लाइसेंस के लिए आवेदन करें – प्रति उपयोगकर्ता दो लाइसेंस मिलेंगे:\n"
            "1. डेमो अकाउंट\n"
            "2. रियल अकाउंट"
        )
    else:
        label = "Click here to download"
        msg = (
            f"📦 Download Grid bot V2 version:\n"
            f"<a href=\"{DOWNLOAD_URL_V2}\">{label}</a>\n\n"
            "Apply for Licence – you will get two licences per user:\n"
            "1. Demo account\n"
            "2. Real account"
        )
    await update.message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)


async def get_setup_instruction_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    if lang == "hi":
        msg = (
            "🛠 <b>V2 सेटअप गाइड (टेलीग्राम से)</b>\n\n"
            "<b>1. लाइसेंस एक्टिवेट करें</b>\n"
            "⚠️ <b>चरण 1:</b> किसी भी ब्रोकर (XM / Exness / Vantage / Roboforex) में पार्टनर कोड जोड़ें:\n"
            "▪ Vantage: <code>VcM6U1DW</code>\n"
            "▪ Roboforex: <code>zrfhm</code>\n"
            "▪ XM: <code>4299V</code>\n"
            "▪ Exness: <code>c_niibgmkreg</code>\n\n"
            "<b>चरण 2:</b> /get_licence_v2 का उपयोग करें और अपनी MT5 आईडी, नाम, ब्रोकर और खाता प्रकार (डेमो/रियल) भेजें – बॉट आपका लाइसेंस एक्टिवेट कर देगा।\n\n"
            "<b>2. MT5 डाउनलोड करें और लॉगिन करें</b>\n"
            "आधिकारिक वेबसाइट metatrader5.com से MT5 डाउनलोड करें।\n"
            "अपने ब्रोकर के User ID, Password और Server से लॉगिन करें।\n\n"
            "<b>3. MetaTrader सेटिंग्स</b>\n"
            "Tools → Options → Expert Advisors:\n"
            "✅ Allow Algorithmic Trading\n"
            "✅ Allow Web Request for listed URL → जोड़ें: https://raw.githubusercontent.com\n\n"
            "<b>4. एल्गो बॉट डाउनलोड करें (dsq_v2)</b>\n"
            "/get_dsq_v2 का उपयोग करें, फिर डाउनलोड की गई फाइल पर डबल‑क्लिक करें → यह MetaTrader में जुड़ जाएगी।\n"
            "Navigator पैनल (दाईं ओर) में dsq_v2 को Expert Advisors के अंतर्गत देखें।\n\n"
            "📹 <b>सेटअप वीडियो:</b> जल्द ही उपलब्ध होगा।"
        )
    else:
        msg = (
            "🛠 <b>V2 Setup Guide (from Telegram)</b>\n\n"
            "<b>1. Activate your Licence</b>\n"
            "⚠️ <b>Step 1:</b> Add the partner code for any broker (XM / Exness / Vantage / Roboforex):\n"
            "▪ Vantage: <code>VcM6U1DW</code>\n"
            "▪ Roboforex: <code>zrfhm</code>\n"
            "▪ XM: <code>4299V</code>\n"
            "▪ Exness: <code>c_niibgmkreg</code>\n\n"
            "<b>Step 2:</b> Use /get_licence_v2 and send your MT5 ID, Name, Broker, and Account type (Demo/Real) – the bot will activate your licence.\n\n"
            "<b>2. Download MT5 &amp; Login</b>\n"
            "Download MT5 from the official website: metatrader5.com\n"
            "Login with your broker’s User ID, Password, and Server.\n\n"
            "<b>3. MetaTrader Settings</b>\n"
            "Tools → Options → Expert Advisors:\n"
            "✅ Allow Algorithmic Trading\n"
            "✅ Allow Web Request for listed URL → Add: https://raw.githubusercontent.com\n\n"
            "<b>4. Download the Algo Bot (dsq_v2)</b>\n"
            "Use /get_dsq_v2, then double‑click the downloaded file → it will be added to MetaTrader.\n"
            "In the Navigator panel (right side), find dsq_v2 under Expert Advisors.\n\n"
            "📹 <b>Setup Video:</b> Coming soon."
        )
    await update.message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)



async def risk_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    if lang == "hi":
        msg = "⚠️ V2 जोखिम जानकारी जल्द ही प्रकाशित की जाएगी।"
    else:
        msg = "⚠️ V2 risk information will be published soon."
    await update.message.reply_text(msg)

# ==================== HANDLER LIST ====================
from handlers.handle_licence_v1 import licence_conv_v1       # V1 licence
from handlers.handle_licence_v2 import licence_conv_v2 # V2 licence (new file)

handlers = [
    licence_conv_v1,          # /get_licence_v1  (must be first, as before)
    licence_conv_v2,       # /get_licence_v2

    CommandHandler("start", start),
    CommandHandler("change_lang", change_lang),

    # V1 commands
    CommandHandler("get_dsq_v1", get_dsq_v1),
    CommandHandler("get_setup_instruction_v1", get_setup_instruction_v1),
    CommandHandler("risk_v1", risk_v1),

    # V2 commands (placeholders)
    CommandHandler("get_dsq_v2", get_dsq_v2),
    CommandHandler("get_setup_instruction_v2", get_setup_instruction_v2),
    CommandHandler("risk_v2", risk_v1),
]


