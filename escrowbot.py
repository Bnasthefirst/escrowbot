import logging
import time
import uuid
import os
from dotenv import load_dotenv

from fastapi import FastAPI, Request, HTTPException
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
import asyncio

load_dotenv()

# ---------------- CONFIG ----------------
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN environment variable is missing")

ADMIN_ID = int(os.getenv("ADMIN_ID") or 0)
BTC_WALLET_ADDRESS = os.getenv("BTC_WALLET")
LTC_USDT_ETH_WALLET_ADDRESS = os.getenv("LTC_USDT_ETH_WALLET_ADDRESS")

# Render provides this automatically
PORT = int(os.getenv("PORT", "8000"))
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME', 'localhost')}{WEBHOOK_PATH}"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Fake balances
user_balances = {}  # user_id → float

# ---------------- MESSAGES & KEYBOARDS (unchanged) ----------------
# ... paste your full MESSAGES dict and MENU_KEYBOARDS here ...
# For brevity, assume they are defined as in your original code

# ---------------- HELPERS ----------------
def get_balance(user_id: int) -> float:
    return user_balances.get(user_id, 0.0)

# ---------------- HANDLERS (same as yours) ----------------
# Paste your async def start(...), menu_handler(...), handle_text(...), handle_check_button(...) here
# They remain exactly the same — no changes needed!

# ---------------- FASTAPI APP ----------------
app = FastAPI()

application: Application = None  # global, initialized in startup

@app.on_event("startup")
async def startup_event():
    global application
    application = (
        Application.builder()
        .token(TOKEN)
        .get_updates_read_timeout(42)   # optional, helps with timeouts
        .build()
    )

    # Add your handlers (same as before)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(handle_check_button, pattern="^check_payment$"))

    await application.initialize()
    await application.start()

    # Set webhook — this tells Telegram to send updates to us
    await application.bot.set_webhook(
        url=WEBHOOK_URL,
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,  # optional: ignore old messages
    )

    logging.info(f"Webhook set to: {WEBHOOK_URL}")


@app.on_event("shutdown")
async def shutdown_event():
    if application:
        await application.stop()
        await application.shutdown()


@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    """Receives all Telegram updates here"""
    if request.headers.get("content-type") == "application/json":
        json_data = await request.json()
        update = Update.de_json(json_data, application.bot)
        if update:
            await application.process_update(update)
            return {"ok": True}
    raise HTTPException(status_code=403, detail="Forbidden")


@app.get("/")
async def root():
    return {"status": "Escrow Bot is running (Webhook mode)"}


# ---------------- MAIN ----------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")



# escrowbot with webhooks and fast api
