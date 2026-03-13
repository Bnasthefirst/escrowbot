import logging
import time
import uuid
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

from fastapi import FastAPI, Request, HTTPException
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

load_dotenv()

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN environment variable is missing")

ADMIN_ID = int(os.getenv("ADMIN_ID") or "0")

BTC_WALLET_ADDRESS = os.getenv("BTC_WALLET")
LTC_USDT_ETH_WALLET_ADDRESS = os.getenv("LTC_USDT_ETH_WALLET_ADDRESS")

PORT = int(os.getenv("PORT", "8000"))
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME', f'localhost:{PORT}')}{WEBHOOK_PATH}"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

user_balances = {}

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
    "ru": {  # ← your ru messages
        # ... full ru content ...
    },
    "zh": {  # ← your zh messages
        # ... full zh content ...
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

def get_balance(user_id: int) -> float:
    return user_balances.get(user_id, 0.0)

# ────────────────────────────────────────────────
# HANDLERS
# ────────────────────────────────────────────────

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
    msg = MESSAGES.get(lang, MESSAGES["en"])

    if text == "English 🇬🇧":
        context.user_data["lang"] = "en"
        await update.message.reply_text(
            msg["main_menu"],
            reply_markup=ReplyKeyboardMarkup(MENU_KEYBOARDS["en"], resize_keyboard=True)
        )

    elif text == "Русский 🇷🇺":
        context.user_data["lang"] = "ru"
        await update.message.reply_text(
            msg["main_menu"],
            reply_markup=ReplyKeyboardMarkup(MENU_KEYBOARDS["ru"], resize_keyboard=True)
        )

    elif text == "中文 🇨🇳":
        context.user_data["lang"] = "zh"
        await update.message.reply_text(
            msg["main_menu"],
            reply_markup=ReplyKeyboardMarkup(MENU_KEYBOARDS["zh"], resize_keyboard=True)
        )

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

    # New Deal
    elif text in ("🆕 New deal", "🆕 Новая сделка", "🆕 新交易"):
        bal = get_balance(user_id)
        if bal <= 0:
            await update.message.reply_text(msg["new_deal_insufficient"].format(bal))
        else:
            await update.message.reply_text(f"Creating new deal... (balance sufficient: ${bal:.2f})")

    # Other menu items ...
    elif text in ("📦 All deals", "📦 Все сделки", "📦 所有交易"):
        await update.message.reply_text(msg["all_deals"])
    # ... etc.


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    state = context.user_data.get("state")
    lang = context.user_data.get("lang", "en")
    msg = MESSAGES.get(lang, MESSAGES["en"])

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

        admin_msg = msg["new_deposit"].format(
            user.id, username, amount, currency, time.strftime('%Y-%m-%d %H:%M:%S')
        )
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg)
        except Exception as e:
            logging.error(f"Failed to notify admin: {e}")

        if currency == "BTC":
            payment_address = BTC_WALLET_ADDRESS
            network_note = "Bitcoin (BTC) network — send only on BTC mainnet!"
        else:
            payment_address = LTC_USDT_ETH_WALLET_ADDRESS
            network_note = {
                "USDT": "ERC20 network (USDT) — IMPORTANT: Do NOT use TRC20, BEP20, OMNI or other chains!",
                "ETH": "Ethereum (ETH) network",
                "LTC": "Litecoin (LTC) network"
            }[currency]

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
    msg = MESSAGES.get(lang, MESSAGES["en"])

    await query.edit_message_text(msg["confirming"])

    time.sleep(5 + time.time() % 3)

    await query.edit_message_text(msg["manual_verify"])


# ────────────────────────────────────────────────
# LIFESPAN
# ────────────────────────────────────────────────

application: Application = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global application
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(handle_check_button, pattern="^check_payment$"))

    await application.initialize()
    await application.start()

    await application.bot.set_webhook(
        url=WEBHOOK_URL,
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )
    logging.info(f"Webhook set to: {WEBHOOK_URL}")

    yield

    await application.stop()
    await application.shutdown()


# ────────────────────────────────────────────────
# APP
# ────────────────────────────────────────────────

app = FastAPI(lifespan=lifespan)


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    if request.headers.get("content-type") == "application/json":
        json_data = await request.json()
        update = Update.de_json(json_data, application.bot)
        if update:
            await application.process_update(update)
            return {"status": "ok"}
    raise HTTPException(status_code=403, detail="Forbidden")


@app.get("/")
async def root():
    return {"status": "Escrow bot webhook running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, log_level="info")
