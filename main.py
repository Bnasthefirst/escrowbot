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

# Paste your full MESSAGES and MENU_KEYBOARDS dictionaries here
# (keeping only "en" for brevity — add ru/zh back if needed)
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
        # ... add remaining keys ...
    },
}

MENU_KEYBOARDS = {
    "en": [
        ["🆕 New deal"],
        ["📦 All deals", "💳 Top Up"],
        ["ℹ️ Info", "👤 Profile"],
        ["💰 Withdrawal", "🛒 Shop"],
        ["💬 CHAT"]
    ],
}

def get_balance(user_id: int) -> float:
    return user_balances.get(user_id, 0.0)

# ────────────────────────────────────────────────
# HANDLERS — define BEFORE lifespan / app
# ────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["English 🇬🇧"]]  # simplified
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Select a language", reply_markup=reply_markup)


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
    elif text == "💳 Top Up":
        bal = get_balance(user_id)
        await update.message.reply_text(
            f"{msg['current_balance'].format(bal)}\n\n{msg['topup_prompt']}"
        )
        context.user_data["state"] = "await_topup_amount"
    # ... add other menu cases ...


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Your full top-up logic here (copy from original)
    # For brevity — paste your complete function body
    pass  # ← replace with real code


async def handle_check_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Your full check button logic here
    pass  # ← replace with real code


# ────────────────────────────────────────────────
# LIFESPAN (modern replacement for on_event)
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
    logging.info(f"Webhook set: {WEBHOOK_URL}")

    yield

    await application.stop()
    await application.shutdown()


# ────────────────────────────────────────────────
# FASTAPI APP
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
