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

# ==========================
# CONFIG
# ==========================
TOKEN = os.environ["BOT_TOKEN"]
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "").strip("/")

# balances stored in memory
# structure: {user_id: {"balance": 0, "withdrawable": 0, "captcha_done": 0, "invites": set()}}
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
        "📌 Commands:\n"
        "⚖️ /balance – Check balance\n"
        "🧩 /captcha2earn – Solve captchas to earn pesos\n"
        "🎲 /dice – Play dice game (odd/even betting)\n"
        "🎰 /scatterspin – Spin slot machine\n"
        "👥 /invite – Invite friends for bonus\n"
        "💵 /withdraw – Withdraw when balance ≥ 888\n"
        "❕ /about – Learn how the bot works"
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    await update.message.reply_text(
        f"⚖ Balance: {user['balance']} pesos\n"
        f"💵 Withdrawable: {user['withdrawable']} pesos"
    )

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if user["withdrawable"] < 888:
        await update.message.reply_text(
            f"🚫 Minimum withdrawable balance is ₱888.\n"
            f"💵 You currently have: ₱{user['withdrawable']}"
        )
    else:
        await update.message.reply_text(
            f"✅ Withdrawal request started for ₱{user['withdrawable']}.\n"
            "📌 Please send your Full Name + GCash number here."
        )
        user["withdrawable"] = 0  # reset withdrawable balance

async def captcha2earn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)

    if user["captcha_done"] >= 50:
        await update.message.reply_text(
            "🚫 You reached 50 captchas.\n"
            "👉 Invite 5 people with /invite to continue earning captchas!"
        )
        return

    # simple captcha (text instead of PNG for Render simplicity)
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    captcha_text = "".join(random.choice(chars) for _ in range(5))
    captcha_answers[update.effective_user.id] = captcha_text

    await update.message.reply_text(
        f"🧩 Captcha challenge:\n\n"
        f"👉 Type this exactly: {captcha_text}"
    )

async def check_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)
    if uid not in captcha_answers:
        return

    answer = captcha_answers[uid]
    if update.message.text.strip().upper() == answer:
        reward = random.randint(1, 10)
        user["balance"] += reward
        user["captcha_done"] += 1
        await update.message.reply_text(
            f"✅ Correct! You earned ₱{reward}.\n"
            f"💰 Balance: ₱{user['balance']}\n"
            f"🧩 Captchas solved: {user['captcha_done']}/50"
        )
    else:
        await update.message.reply_text("❌ Wrong captcha! Try again with /captcha2earn")

    del captcha_answers[uid]

async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    await update.message.reply_text(
        "👥 Invite friends!\n\n"
        "📌 Share this bot link with your friends:\n"
        f"https://t.me/{context.bot.username}?start={update.effective_user.id}\n\n"
        "🎁 When 5 of them use your link, you can continue captcha earning.\n"
        "💵 You earn ₱77 per invite!"
    )

async def dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("🎲 Usage: /dice <odd/even> <amount>")
        return

    choice, amount = args[0].lower(), int(args[1])
    user = get_user(update.effective_user.id)

    if user["balance"] < amount:
        await update.message.reply_text("🚫 Not enough balance!")
        return

    roll = random.randint(1, 6)
    result = "odd" if roll % 2 else "even"

    if choice == result:
        win = amount * 2
        user["balance"] += win
        user["withdrawable"] += amount  # only stake becomes withdrawable
        await update.message.reply_text(f"🎲 You rolled {roll} ({result}). ✅ You won ₱{win}!")
    else:
        user["balance"] -= amount
        await update.message.reply_text(f"🎲 You rolled {roll} ({result}). ❌ You lost ₱{amount}!")

async def scatterspin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("🎰 Usage: /scatterspin <amount>")
        return

    bet = int(args[0])
    user = get_user(update.effective_user.id)

    if user["balance"] < bet:
        await update.message.reply_text("🚫 Not enough balance!")
        return

    symbols = ["🍒", "7️⃣", "⭐", "💎"]
    spin = [random.choice(symbols) for _ in range(3)]
    result = " ".join(spin)

    if len(set(spin)) == 1:  # jackpot
        win = bet * 5
        user["balance"] += win
        user["withdrawable"] += bet
        await update.message.reply_text(f"🎰 {result}\n💎 JACKPOT! You won ₱{win}!")
    elif len(set(spin)) == 2:  # two match
        win = bet * 2
        user["balance"] += win
        user["withdrawable"] += bet
        await update.message.reply_text(f"🎰 {result}\n⭐ Nice! You won ₱{win}!")
    else:  # lose
        user["balance"] -= bet
        await update.message.reply_text(f"🎰 {result}\n❌ You lost ₱{bet}!")

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❕ About this bot:\n\n"
        "🧩 Solve captchas to earn 1–10 pesos each.\n"
        "👥 Invite friends to unlock captcha after 50 solves.\n"
        "🎲 Play dice (odd/even) and double your bet.\n"
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
    app.add_handler(CommandHandler("withdraw", withdraw))
    app.add_handler(CommandHandler("captcha2earn", captcha2earn))
    app.add_handler(CommandHandler("invite", invite))
    app.add_handler(CommandHandler("dice", dice))
    app.add_handler(CommandHandler("scatterspin", scatterspin))
    app.add_handler(CommandHandler("about", about))

    # Captcha answers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_captcha))

    # Webhook mode (Render)
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        url_path=TOKEN,
        webhook_url=f"{RENDER_URL}/{TOKEN}",
    )

if __name__ == "__main__":
    main()
