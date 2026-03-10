import logging
import os
from dotenv import load_dotenv
import time
import uuid
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

load_dotenv()           # ← this line is new & important
# ---------------- CONFIG ----------------
# ...
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN environment variable is missing")

ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Wallet addresses 

BTC_WALLET_ADDRESS = os.getenv("BTC_WALLET")
LTC_USDT_ETH_WALLET_ADDRESS = os.getenv("LTC_USDT_ETH_WALLET_ADDRESS")




logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Fake user balances (later replace with database)
user_balances = {}  # user_id → float

# ---------------- MESSAGES (multilingual) ----------------
MESSAGES = {
    "en": {
        "select_language": "Select a language",
        "main_menu": "Main menu:",
        "current_balance": "Current balance: ${:.2f}",
        "topup_prompt": "Enter the amount of $ to top up your balance\nMinimum: $1\nExample: 10, 0.30, 1.5",
        "min_amount": "Minimum amount is $1. Try again.",
        "invalid_number": "Please enter a valid number (e.g. 10 or 0.30).",
        "choose_crypto": "Choose cryptocurrency for top-up of ${:.2f}:",
        "topup_cancelled": "Top-up cancelled.",
        "invalid_crypto": "Please choose one of the options or Cancel.",
        "new_deposit": "New deposit request!\nUser: {} (@{})\nAmount: ${:.2f}\nCurrency: {}\nTime: {}",
        "invoice_title": "🔒 Invoice #{}\n\nPayment address:\n{}\n\nAmount: {:.2f} {}\n\n",
        "check_button": "✅ Check payment",
        "confirming": "Please wait, confirming payment... ⏳",
        "manual_verify": "Confirmation in progress.\nPlease be patient — our admin will verify manually.\nContact support if needed.",
        "withdrawal_min": "Withdrawal is possible only from ${:.2f}\nYour balance: ${:.2f}\nPlease top up first!",
        "new_deal_insufficient": "You have ${:.2f}, kindly top up to create a new deal",
        "all_deals": "Showing all deals...",
        "profile": "Your profile",
        "info": "Bot information",
        "shop": "Opening shop...",
        "chat": "Starting live chat...",
    },
    "ru": {
        "select_language": "Выберите язык",
        "main_menu": "Главное меню:",
        "current_balance": "Текущий баланс: ${:.2f}",
        "topup_prompt": "Введите сумму в $ для пополнения баланса\nМинимум: $1\nПример: 10, 0.30, 1.5",
        "min_amount": "Минимальная сумма $1. Попробуйте снова.",
        "invalid_number": "Введите корректное число (например 10 или 0.30).",
        "choose_crypto": "Выберите криптовалюту для пополнения на ${:.2f}:",
        "topup_cancelled": "Пополнение отменено.",
        "invalid_crypto": "Выберите один из вариантов или Отмена.",
        "new_deposit": "Новый запрос на пополнение!\nПользователь: {} (@{})\nСумма: ${:.2f}\nВалюта: {}\nВремя: {}",
        "invoice_title": "🔒 Счет #{}\n\nАдрес для оплаты:\n{}\n\nСумма: {:.2f} {}\n\n",
        "check_button": "✅ Проверить оплату",
        "confirming": "Подождите, проверяем оплату... ⏳",
        "manual_verify": "Проверка в процессе.\nБудьте терпеливы — администратор проверит вручную.\nОбратитесь в поддержку при необходимости.",
        "withdrawal_min": "Вывод возможен только от ${:.2f}\nВаш баланс: ${:.2f}\nПополните баланс!",
        "new_deal_insufficient": "У вас ${:.2f}, пожалуйста пополните баланс, чтобы создать новую сделку",
        "all_deals": "Показ всех сделок...",
        "profile": "Ваш профиль",
        "info": "Информация о боте",
        "shop": "Открытие магазина...",
        "chat": "Запуск живого чата...",
    },
    "zh": {
        "select_language": "选择语言",
        "main_menu": "主菜单：",
        "current_balance": "当前余额：${:.2f}",
        "topup_prompt": "输入要充值的美元金额\n最低：$1\n示例：10、0.30、1.5",
        "min_amount": "最低金额为 $1。请重试。",
        "invalid_number": "请输入有效数字（例如 10 或 0.30）。",
        "choose_crypto": "选择用于充值 ${:.2f} 的加密货币：",
        "topup_cancelled": "充值已取消。",
        "invalid_crypto": "请选择选项或取消。",
        "new_deposit": "新的充值请求！\n用户：{} (@{})\n金额：${:.2f}\n货币：{}\n时间：{}",
        "invoice_title": "🔒 发票 #{}\n\n付款地址：\n{}\n\n金额：{:.2f} {}\n\n",
        "check_button": "✅ 检查付款",
        "confirming": "请稍候，正在确认付款... ⏳",
        "manual_verify": "确认中。\n请耐心等待 — 管理员将手动验证。\n如有需要请联系支持。",
        "withdrawal_min": "提现最低金额 ${:.2f}\n您的余额：${:.2f}\n请先充值！",
        "new_deal_insufficient": "您的余额为 ${:.2f}，请充值后创建新交易",
        "all_deals": "显示所有交易...",
        "profile": "您的个人资料",
        "info": "机器人信息",
        "shop": "打开商店...",
        "chat": "启动实时聊天...",
    }
}

MENU_KEYBOARDS = {
    "en": [
        ["🆕 New deal"],
        ["📦 All deals", "💳 Top Up"],
        ["ℹ️ Info", "👤 Profile"],
        ["💰 Withdrawal", "🛒 Shop"],
        ["💬 CHAT"]
    ],
    "ru": [
        ["🆕 Новая сделка"],
        ["📦 Все сделки", "💳 Пополнить"],
        ["ℹ️ Инфо", "👤 Профиль"],
        ["💰 Вывод", "🛒 Магазин"],
        ["💬 ЧАТ"]
    ],
    "zh": [
        ["🆕 新交易"],
        ["📦 所有交易", "💳 充值"],
        ["ℹ️ 信息", "👤 个人资料"],
        ["💰 提现", "🛒 商店"],
        ["💬 聊天"]
    ]
}

# ---------------- HELPERS ----------------
def get_balance(user_id: int) -> float:
    return user_balances.get(user_id, 0.0)

# ---------------- HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["English 🇬🇧", "Русский 🇷🇺", "中文 🇨🇳"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "Select a language / Выберите язык / 选择语言",
        reply_markup=reply_markup
    )

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    msg = MESSAGES[lang]

    # Language selection
    if text == "English 🇬🇧":
        context.user_data["lang"] = "en"
        await update.message.reply_text(msg["main_menu"], reply_markup=ReplyKeyboardMarkup(MENU_KEYBOARDS["en"], resize_keyboard=True))

    elif text == "Русский 🇷🇺":
        context.user_data["lang"] = "ru"
        await update.message.reply_text(msg["main_menu"], reply_markup=ReplyKeyboardMarkup(MENU_KEYBOARDS["ru"], resize_keyboard=True))

    elif text == "中文 🇨🇳":
        context.user_data["lang"] = "zh"
        await update.message.reply_text(msg["main_menu"], reply_markup=ReplyKeyboardMarkup(MENU_KEYBOARDS["zh"], resize_keyboard=True))

    # Top Up
    elif text in ("💳 Top Up", "💳 Пополнить", "💳 充值"):
        bal = get_balance(user_id)
        await update.message.reply_text(
            f"{msg['current_balance'].format(bal)}\n\n{msg['topup_prompt']}"
        )
        context.user_data["state"] = "await_topup_amount"

    # Withdrawal
    elif text in ("💰 Withdrawal", "💰 Вывод", "💰 提现"):
        min_wd = 4.50
        bal = get_balance(user_id)
        await update.message.reply_text(msg["withdrawal_min"].format(min_wd, bal))

    # New Deal – now checks balance
    elif text in ("🆕 New deal", "🆕 Новая сделка", "🆕 新交易"):
        bal = get_balance(user_id)
        if bal <= 0:
            await update.message.reply_text(msg["new_deal_insufficient"].format(bal))
        else:
            await update.message.reply_text("Creating new deal... (balance sufficient: ${:.2f})".format(bal))

    # Other menu actions
    elif text in ("📦 All deals", "📦 Все сделки", "📦 所有交易"):
        await update.message.reply_text(msg["all_deals"])
    elif text in ("ℹ️ Info", "ℹ️ Инфо", "ℹ️ 信息"):
        await update.message.reply_text(msg["info"])
    elif text in ("👤 Profile", "👤 Профиль", "👤 个人资料"):
        await update.message.reply_text(msg["profile"])
    elif text in ("🛒 Shop", "🛒 Магазин", "🛒 商店"):
        await update.message.reply_text(msg["shop"])
    elif text in ("💬 CHAT", "💬 ЧАТ", "💬 聊天"):
        await update.message.reply_text(msg["chat"])

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    state = context.user_data.get("state")
    lang = context.user_data.get("lang", "en")
    msg = MESSAGES[lang]

    if state == "await_topup_amount":
        try:
            amount = float(text.replace(",", "."))
            if amount < 1:
                await update.message.reply_text(msg["min_amount"])
                return
        except ValueError:
            await update.message.reply_text(msg["invalid_number"])
            return

        context.user_data["topup_amount"] = amount

        cancel_text = "Cancel ❌" if lang == "en" else "Отмена ❌" if lang == "ru" else "取消 ❌"
        keyboard = [
            [KeyboardButton("USDT")],
            [KeyboardButton("BTC")],
            [KeyboardButton("ETH")],
            [KeyboardButton("LTC")],
            [KeyboardButton(cancel_text)]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

        await update.message.reply_text(
            msg["choose_crypto"].format(amount),
            reply_markup=reply_markup
        )
        context.user_data["state"] = "await_crypto_choice"

    elif state == "await_crypto_choice":
        if "Cancel" in text or "Отмена" in text or "取消" in text:
            context.user_data.clear()
            await update.message.reply_text(msg["topup_cancelled"])
            return

        if text not in ("USDT", "BTC", "ETH", "LTC"):
            await update.message.reply_text(msg["invalid_crypto"])
            return

        amount = context.user_data.get("topup_amount")
        currency = text
        user = update.effective_user
        username = user.username or "No username"

        # Notify admin
        admin_msg = msg["new_deposit"].format(
            user.id, username, amount, currency, time.strftime('%Y-%m-%d %H:%M:%S')
        )
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg)
        except Exception as e:
            logging.error(f"Failed to notify admin: {e}")

        # Select correct wallet address and network note
        if currency == "BTC":
            payment_address = BTC_WALLET_ADDRESS
            network_note = "Bitcoin (BTC) network — send only on BTC mainnet!"
        else:
            payment_address = LTC_USDT_ETH_WALLET_ADDRESS
            if currency == "USDT":
                network_note = "ERC20 network (USDT) — IMPORTANT: Do NOT use TRC20, BEP20, OMNI or other chains!"
            elif currency == "ETH":
                network_note = "Ethereum (ETH) network"
            elif currency == "LTC":
                network_note = "Litecoin (LTC) network"

        # Build invoice message
        invoice_id = str(uuid.uuid4())[:12]
        invoice_text = (
            f"{msg['invoice_title'].format(invoice_id, payment_address, amount, currency)}\n"
            f"Network: {network_note}\n\n"
            f"❗ Double-check address and network before sending!\n"
            f"❗ Send exactly {amount:.8f} {currency} — do not round"
        )

        keyboard = [[InlineKeyboardButton(msg["check_button"], callback_data="check_payment")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(invoice_text, reply_markup=reply_markup)

        context.user_data.pop("state", None)
        context.user_data.pop("topup_amount", None)

async def handle_check_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    lang = context.user_data.get("lang", "en")
    msg = MESSAGES[lang]

    await query.edit_message_text(msg["confirming"])

    # Fake delay (in real bot → check blockchain here)
    time.sleep(5 + time.time() % 3)

    await query.edit_message_text(msg["manual_verify"])

# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_check_button, pattern="^check_payment$"))

    print("Bot running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
