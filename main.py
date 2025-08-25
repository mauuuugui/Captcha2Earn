import os
import random
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import telegram
print("PTB version:", telegram.__version__)

TOKEN = os.environ["BOT_TOKEN"]

# ==========================
# USER DATA
# ==========================
user_data = {}
captcha_answers = {}

# ==========================
# HELPER
# ==========================
def get_user(uid):
    return user_data.setdefault(uid, {"balance": 0, "withdrawable": 0, "captcha_done": 0, "invites": set()})

# ==========================
# COMMANDS
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user(user.id)
    await update.message.reply_text(
        f"👋 Welcome {user.first_name}!\n\n"
        "Commands:\n"
        "⚖️ /balance – Show your balance\n"
        "🧩 /captcha2earn – Solve captchas\n"
        "🎲 /dice – Bet on dice (odd/even)\n"
        "🎰 /scatterspin – Slot machine spin\n"
        "👥 /invite – Invite friends for bonus\n"
        "💵 /withdraw – Withdraw when balance ≥ 888\n"
        "❕ /about – Learn how the bot works"
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    await update.message.reply_text(
        f"⚖️ Balance: {user['balance']} pesos\n"
        f"💵 Withdrawable: {user['withdrawable']} pesos"
    )

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❕ About this bot:\n\n"
        "🧩 Solve captchas (/captcha2earn) to earn pesos.\n"
        "👥 Invite friends (/invite) to get bonuses.\n"
        "🎲 Play dice (odd/even) to win.\n"
        "🎰 Spin scatter machine for jackpots.\n"
        "💵 Only money earned in games becomes withdrawable.\n"
        "⚖ Minimum withdrawal: ₱888."
    )

# ==========================
# MAIN
# ==========================
def main():
    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("about", about))

    print("Bot is running with polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
