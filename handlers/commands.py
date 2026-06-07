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
            "👋 आपका स्वागत है! उपलब्ध कमांड्स: [अभी सब कुछ फ्री है]\n\n"
            "/start – यह मेनू दिखाएं\n"
            "/get_dsq_v1 – ग्रिड बॉट V1 संस्करण डाउनलोड करें\n"
            "/get_licence_v1 – लाइसेंस फॉर्म\n"
            "/get_setup_instruction_v1 – सेटअप निर्देश वीडियो लिंक\n"
            "/risk_v1 – चलाने से पहले अपना जोखिम जानें\n"
            "/change_lang – भाषा बदलें (English ↔ हिंदी)"
        )
    else:
        msg = (
            "👋 Welcome! Available commands: [Everything is free for Now]\n\n"
            "/start – Show this menu\n"
            "/get_dsq_v1 – Download Grid bot V1 version\n"
            "/get_licence_v1 – Licence form\n"
            "/get_setup_instruction_v1 – Setup Instruction Video links\n"
            "/risk_v1 – Know your risk before you run\n"
            "/change_lang – Toggle language (English ↔ हिंदी)"
        )
    await update.message.reply_text(msg)

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
            "🌐 <b>Setup Guide(from DSQ Web Page)</b>\n"
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

# ==================== HANDLER LIST ====================
# Import the licence conversation from its own file
from handlers.handle_licence import licence_conv

handlers = [
    CommandHandler("start", start),
    CommandHandler("change_lang", change_lang),
    CommandHandler("get_dsq_v1", get_dsq_v1),
    CommandHandler("get_setup_instruction_v1", get_setup_instruction_v1),
    CommandHandler("risk_v1", risk_v1),
    licence_conv,   # /get_licence_v1
]