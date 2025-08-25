import os
import random
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    MessageHandler, filters
)

# ==========================
# CONFIG
# ==========================
TOKEN = os.environ["BOT_TOKEN"]

# balances stored in memory (for demo; use DB for production)
user_data = {}
captcha_answers = {}
captcha_count = {}
invites = {}

# ==========================
# COMMANDS
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data.setdefault(user.id, {"balance": 0, "withdrawable": 0})
    captcha_count.setdefault(user.id, 0)
    invites.setdefault(user.id, 0)
    await update.message.reply_text(
        f"👋 Welcome {user.first_name}!\n\n"
        "Here’s how you can earn pesos 💰:\n"
        "🧩 Solve captchas with /captcha2earn\n"
        "🎲 Play dice with /dice\n"
        "🎰 Try slots with /scatterspin\n"
        "👥 Invite friends with /invite\n"
        "⚖️ Check your pesos with /balance\n"
        "💵 Withdraw when you reach ₱888 using /withdraw\n\n"
        "Type /about to learn more."
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = user_data.get(user.id, {"balance": 0, "withdrawable": 0})
    await update.message.reply_text(
        f"⚖️ Total Balance: ₱{data['balance']}\n"
        f"💵 Withdrawable Balance: ₱{data['withdrawable']}\n"
        "➡️ You need ₱888 withdrawable to request payout."
    )

# ==========================
# CAPTCHA
# ==========================
async def captcha2earn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    count = captcha_count.get(user.id, 0)
    if count >= 50 and invites.get(user.id, 0) < 5:
        await update.message.reply_text(
            "🚫 You’ve reached 50 captchas.\n"
            "👉 Invite at least 5 friends using /invite to continue earning captchas!"
        )
        return

    # simple text captcha (letters & numbers)
    text = ''.join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=5))
    captcha_answers[user.id] = text
    await update.message.reply_text(
        f"🧩 Type this captcha to earn:\n\n{text}"
    )

async def check_captcha_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in captcha_answers:
        attempt = update.message.text.strip()
        if attempt.upper() == captcha_answers[user.id]:
            reward = random.randint(1, 10)
            user_data[user.id]["balance"] += reward
            captcha_count[user.id] += 1
            await update.message.reply_text(
                f"✅ Correct! You earned ₱{reward}.\n"
                f"📊 Total Captchas Solved: {captcha_count[user.id]}\n"
                f"💰 Balance: ₱{user_data[user.id]['balance']}"
            )
        else:
            await update.message.reply_text("❌ Wrong captcha! Try /captcha2earn again.")
        del captcha_answers[user.id]

# ==========================
# INVITE
# ==========================
async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data[user.id]["balance"] += 77
    invites[user.id] += 1
    await update.message.reply_text(
        "👥 Invite System\n\n"
        "Every invite gives you ₱77 🎉\n"
        f"✅ Total invites so far: {invites[user.id]}\n"
        f"💰 Balance: ₱{user_data[user.id]['balance']}\n\n"
        "👉 Share your bot link and earn more!"
    )

# ==========================
# DICE GAME
# ==========================
async def dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 2 or args[0].lower() not in ["odd", "even"]:
        await update.message.reply_text(
            "🎲 Dice Game Instructions:\n\n"
            "Use /dice <odd/even> <amount>\n"
            "Example: /dice odd 50\n\n"
            "➡️ If the dice matches your choice, you win 2x your bet into withdrawable balance.\n"
            "➡️ If not, you lose your bet."
        )
        return

    choice, bet_str = args
    try:
        bet = int(bet_str)
    except ValueError:
        await update.message.reply_text("❌ Bet amount must be a number.")
        return

    user = update.effective_user
    if user_data[user.id]["balance"] < bet:
        await update.message.reply_text("🚫 Not enough balance for this bet.")
        return

    roll = random.randint(1, 6)
    user_data[user.id]["balance"] -= bet
    result = "even" if roll % 2 == 0 else "odd"

    if result == choice.lower():
        winnings = bet * 2
        user_data[user.id]["withdrawable"] += winnings
        await update.message.reply_text(
            f"🎲 You rolled {roll} ({result})\n✅ You win ₱{winnings}!\n"
            f"💵 Withdrawable Balance: ₱{user_data[user.id]['withdrawable']}"
        )
    else:
        await update.message.reply_text(
            f"🎲 You rolled {roll} ({result})\n❌ You lost your bet.\n"
            f"💵 Withdrawable Balance: ₱{user_data[user.id]['withdrawable']}"
        )

# ==========================
# SCATTER SPIN
# ==========================
async def scatterspin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 1:
        await update.message.reply_text(
            "🎰 Scatter Spin Instructions:\n\n"
            "Use /scatterspin <amount>\n"
            "Example: /scatterspin 100\n\n"
            "➡️ If you get 3 same symbols, you win 5x your bet into withdrawable balance.\n"
            "➡️ If 2 match, you win 2x.\n"
            "➡️ Otherwise, you lose your bet."
        )
        return

    try:
        bet = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Bet amount must be a number.")
        return

    user = update.effective_user
    if user_data[user.id]["balance"] < bet:
        await update.message.reply_text("🚫 Not enough balance.")
        return

    user_data[user.id]["balance"] -= bet
    symbols = ["🍒", "7️⃣", "⭐", "💎"]
    spin = [random.choice(symbols) for _ in range(3)]
    result = " ".join(spin)

    if spin[0] == spin[1] == spin[2]:
        winnings = bet * 5
        user_data[user.id]["withdrawable"] += winnings
        msg = f"🎰 {result}\n🎉 JACKPOT! You won ₱{winnings}"
    elif spin[0] == spin[1] or spin[1] == spin[2] or spin[0] == spin[2]:
        winnings = bet * 2
        user_data[user.id]["withdrawable"] += winnings
        msg = f"🎰 {result}\n✨ Nice! You won ₱{winnings}"
    else:
        msg = f"🎰 {result}\n❌ You lost your bet."

    await update.message.reply_text(msg + f"\n💵 Withdrawable Balance: ₱{user_data[user.id]['withdrawable']}")

# ==========================
# WITHDRAW
# ==========================
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user_data[user.id]["withdrawable"] < 888:
        await update.message.reply_text(
            "🚫 You need at least ₱888 withdrawable balance to withdraw."
        )
    else:
        await update.message.reply_text(
            f"💵 Withdrawal request started for ₱{user_data[user.id]['withdrawable']}!\n"
            "👉 Please send your Full Name + GCash number."
        )
        user_data[user.id]["withdrawable"] = 0

# ==========================
# ABOUT
# ==========================
async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ Bot Instructions:\n\n"
        "🧩 /captcha2earn → Solve captcha to earn (1-10 per captcha)\n"
        "🎲 /dice → Bet odd/even. Win 2x bet (withdrawable).\n"
        "🎰 /scatterspin → Slot machine! 3 match = 5x bet, 2 match = 2x bet.\n"
        "👥 /invite → Invite friends, earn ₱77 each.\n"
        "⚖️ /balance → Check total & withdrawable pesos.\n"
        "💵 /withdraw → Withdraw when you reach ₱888 withdrawable.\n\n"
        "👉 Play games to convert balance into withdrawable!"
    )

# ==========================
# MAIN (Render Webhook)
# ==========================
def main():
    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("captcha2earn", captcha2earn))
    app.add_handler(CommandHandler("invite", invite))
    app.add_handler(CommandHandler("withdraw", withdraw))
    app.add_handler(CommandHandler("dice", dice))
    app.add_handler(CommandHandler("scatterspin", scatterspin))
    app.add_handler(CommandHandler("about", about))

    # Captcha answers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_captcha_text))

    # Webhook for Render
    port = int(os.environ.get("PORT", 8443))
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"{os.environ['RENDER_EXTERNAL_URL'].strip('/')}/{TOKEN}"
    )

if __name__ == "__main__":
    main()
