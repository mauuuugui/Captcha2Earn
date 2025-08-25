import os
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

TOKEN = os.environ["BOT_TOKEN"]

# ==========================
# USER DATA
# ==========================
user_data = {}
captcha_answers = {}

def get_user(uid):
    return user_data.setdefault(uid, {"balance": 0, "withdrawable": 0, "captcha_done": 0, "invites": set()})

# ==========================
# COMMANDS
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    await update.message.reply_text(
        f"👋 Welcome {update.effective_user.first_name}!\n\n"
        "Commands:\n"
        "⚖️ /balance – Check balance\n"
        "🧩 /captcha2earn – Solve captchas\n"
        "🎲 /dice <odd/even> <amount> – Bet on dice\n"
        "🎰 /scatterspin <amount> – Slot spin\n"
        "👥 /invite – Invite friends for bonus\n"
        "💵 /withdraw – Withdraw when withdrawable ≥ 888\n"
        "❕ /about – Learn how it works"
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    await update.message.reply_text(
        f"⚖️ Balance: {user['balance']} pesos\n"
        f"💵 Withdrawable: {user['withdrawable']} pesos"
    )

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❕ *About this bot:*\n\n"
        "🧩 Solve captchas (/captcha2earn) to earn 1–10 pesos.\n"
        "👥 Invite friends (/invite) to unlock captcha after 50 solves and get ₱77 each.\n"
        "🎲 Play dice (odd/even) – betting increases withdrawable balance.\n"
        "🎰 Spin scatter machine for jackpots – wins increase withdrawable balance.\n"
        "💵 Minimum withdrawal: ₱888.\n"
        "⚖ Withdrawable is earned only through games.",
        parse_mode="Markdown"
    )

# ==========================
# CAPTCHA
# ==========================
async def captcha2earn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if user["captcha_done"] >= 50 and len(user["invites"]) < 5:
        await update.message.reply_text(
            "🚫 50 captchas done.\nInvite 5 friends with /invite to continue earning!"
        )
        return
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    captcha_text = "".join(random.choice(chars) for _ in range(5))
    captcha_answers[update.effective_user.id] = captcha_text
    await update.message.reply_text(f"🧩 Captcha: Type this exactly -> {captcha_text}")

async def check_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)
    if uid not in captcha_answers:
        return
    if update.message.text.strip().upper() == captcha_answers[uid]:
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

# ==========================
# INVITE
# ==========================
async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    await update.message.reply_text(
        "👥 Invite friends!\n"
        f"Share your bot link: https://t.me/{context.bot.username}?start={update.effective_user.id}\n"
        "🎁 You earn ₱77 per invite.\n"
        "📌 After 5 invites, you can continue captcha earning!"
    )

# ==========================
# WITHDRAW
# ==========================
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if user["withdrawable"] < 888:
        await update.message.reply_text(
            f"🚫 Minimum withdrawable balance is ₱888.\n"
            f"💵 Current withdrawable: ₱{user['withdrawable']}"
        )
        return
    await update.message.reply_text(
        f"✅ Withdrawal request started for ₱{user['withdrawable']}.\n"
        "📌 Send Full Name + GCash number here."
    )
    user["withdrawable"] = 0

# ==========================
# DICE GAME
# ==========================
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
        user["withdrawable"] += amount
        await update.message.reply_text(f"🎲 Rolled {roll} ({result}) ✅ You won ₱{win}!")
    else:
        user["balance"] -= amount
        await update.message.reply_text(f"🎲 Rolled {roll} ({result}) ❌ You lost ₱{amount}!")

# ==========================
# SCATTER SPIN
# ==========================
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

# ==========================
# MAIN
# ==========================
def main():
    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("captcha2earn", captcha2earn))
    app.add_handler(CommandHandler("invite", invite))
    app.add_handler(CommandHandler("withdraw", withdraw))
    app.add_handler(CommandHandler("dice", dice))
    app.add_handler(CommandHandler("scatterspin", scatterspin))

    # Captcha answers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_captcha))

    print("Bot is running with polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
