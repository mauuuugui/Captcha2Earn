import os
import random
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ==========================
# CONFIG
# ==========================
TOKEN = os.environ["BOT_TOKEN"]

# In-memory store (use a DB for production)
# user_data[user_id] = {"balance": int, "withdrawable": int}
user_data = {}
# captcha tracking
captcha_answers = {}     # pending answer per user
captcha_count = {}       # total solved per user
invites_done = {}        # invites per user

WITHDRAW_REQUIRED = 888
INVITE_REWARD = 77

# Single-PNG captcha settings
CAPTCHA_FILE = "captcha.png"     # place captcha.png at repo root
CAPTCHA_ANSWER = "abcd123"       # change to the text in captcha.png


# ==========================
# UTILITIES
# ==========================
def ensure_user(user_id: int):
    return user_data.setdefault(user_id, {"balance": 0, "withdrawable": 0})

def get_balances_text(user_id: int) -> str:
    data = ensure_user(user_id)
    return (
        f"💰 Playable Balance: ₱{data['balance']}\n"
        f"💵 Withdrawable Balance: ₱{data['withdrawable']}"
    )


# ==========================
# CORE COMMANDS
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user.id)
    await update.message.reply_text(
        f"👋 Welcome, {user.first_name}!\n\n"
        "Here’s what I can do:\n"
        "⚖️ /balance – show balances & withdraw rule\n"
        "🧩 /captcha2earn – solve captcha (₱1–₱10 each). After 50 solves, invite 5 friends to continue.\n"
        "👥 /invite – +₱77 per invite (playable only)\n"
        "🎲 /dice <odd|even> <bet> – guess parity, win 2× bet (winnings become withdrawable)\n"
        "🎰 /scatterspin <bet> – slot machine; 2× or 5× wins (winnings become withdrawable)\n"
        "💵 /withdraw – need ₱888 withdrawable to cash out\n"
        "❕ /about – full guide"
    )

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❕ About this bot\n\n"
        "🧩 /captcha2earn – See a captcha image. Type the exact letters/numbers to earn ₱1–₱10.\n"
        "  • After **50 correct** captchas, you must **invite 5 friends** (use /invite) to continue captcha earning.\n\n"
        "👥 /invite – Each invite gives **₱77** to your **playable** balance.\n\n"
        "🎲 /dice – Format: `/dice odd 50` or `/dice even 100`\n"
        "  • If you guessed correctly, you **win 2× bet**.\n"
        "  • Winnings are added to **both balances** (playable and withdrawable).\n"
        "  • Losing only deducts from **playable**.\n\n"
        "🎰 /scatterspin – Format: `/scatterspin 50`\n"
        "  • 3 same symbols = **5× bet**\n"
        "  • 2 same symbols = **2× bet**\n"
        "  • No match = lose bet\n"
        "  • **Winnings** go to both balances; **losses** deduct from playable.\n\n"
        "⚖️ /balance – Shows your **playable** and **withdrawable** balances.\n"
        f"💵 /withdraw – You can withdraw when **withdrawable ≥ ₱{WITHDRAW_REQUIRED}**.\n"
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = get_balances_text(user_id)
    await update.message.reply_text(
        f"⚖️ Your balances:\n{text}\n\n"
        f"🔒 Withdrawal unlocks at **₱{WITHDRAW_REQUIRED}** withdrawable."
    )

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = ensure_user(user_id)
    if data["withdrawable"] < WITHDRAW_REQUIRED:
        await update.message.reply_text(
            "🚫 Not enough withdrawable balance.\n"
            f"Required: ₱{WITHDRAW_REQUIRED}\n"
            f"Your withdrawable: ₱{data['withdrawable']}\n\n"
            "🎮 Tip: Win in /dice or /scatterspin to increase withdrawable."
        )
        return

    # Proceed with withdrawal
    amount = data["withdrawable"]
    data["withdrawable"] = 0
    await update.message.reply_text(
        f"✅ Withdrawal request started for **₱{amount}**.\n"
        "Please send your **Full Name + GCash number** here 📲"
    )


# ==========================
# CAPTCHA EARNING
# ==========================
async def captcha2earn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    solved = captcha_count.get(user_id, 0)
    invites = invites_done.get(user_id, 0)

    if solved >= 50 and invites < 5:
        await update.message.reply_text(
            "🧩 You already solved **50 captchas**.\n"
            "🔓 To continue earning from captchas, please **invite 5 friends** using /invite.\n"
            f"📊 Invites so far: {invites}/5"
        )
        return

    # store pending answer
    captcha_answers[user_id] = CAPTCHA_ANSWER.lower()

    # send image
    try:
        with open(CAPTCHA_FILE, "rb") as img:
            await update.message.reply_photo(
                img,
                caption=(
                    "🧩 **Captcha Challenge**\n"
                    "Type exactly the letters/numbers you see to earn **₱1–₱10**.\n"
                    "➡️ Reply in this chat."
                )
            )
    except FileNotFoundError:
        await update.message.reply_text(
            "❗ Captcha image not found. Please add `captcha.png` to the project root."
        )

async def _award_captcha(user_id: int) -> int:
    data = ensure_user(user_id)
    reward = random.randint(1, 10)
    data["balance"] += reward
    captcha_count[user_id] = captcha_count.get(user_id, 0) + 1
    return reward

async def check_captcha_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in captcha_answers:
        return  # nothing pending

    msg = (update.message.text or "").strip().lower()
    correct = captcha_answers[user_id]
    del captcha_answers[user_id]

    if msg == correct:
        reward = await _award_captcha(user_id)
        data = ensure_user(user_id)
        await update.message.reply_text(
            f"✅ Correct! You earned **₱{reward}**.\n"
            f"{get_balances_text(user_id)}\n"
            f"📊 Captchas solved: {captcha_count[user_id]}/50\n"
            "ℹ️ After 50 solves, invite 5 friends via /invite to continue."
        )
    else:
        await update.message.reply_text("❌ Wrong captcha. Try /captcha2earn again.")


# ==========================
# INVITE SYSTEM
# ==========================
async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = ensure_user(user_id)

    invites_done[user_id] = invites_done.get(user_id, 0) + 1
    data["balance"] += INVITE_REWARD

    await update.message.reply_text(
        "👥 **Invite & Earn**\n"
        f"🎁 You received **₱{INVITE_REWARD}** (playable).\n"
        f"📊 Invites: {invites_done[user_id]}\n\n"
        "Tip: Share your bot with friends! After **50 captchas**, you’ll need **5 invites** to keep earning from captchas.\n"
        f"{get_balances_text(user_id)}"
    )


# ==========================
# DICE GAME (ODD/EVEN)
# ==========================
async def dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Usage: /dice odd 50  OR  /dice even 100
    Win: +bet to playable and +bet to withdrawable (net +bet)
    Lose: -bet from playable
    """
    user_id = update.effective_user.id
    data = ensure_user(user_id)

    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            "🎲 **Dice Game – Odd/Even**\n"
            "Format: `/dice odd 50` or `/dice even 100`\n"
            "• Guess the parity of a 1–6 roll.\n"
            "• Correct = **win 2× bet** (you gain +bet net).\n"
            "• Wrong = **lose bet** (playable only).\n"
            "• Winnings add to **withdrawable** too."
        )
        return

    choice = args[0].lower()
    if choice not in ("odd", "even"):
        await update.message.reply_text("❗ First argument must be `odd` or `even`.")
        return

    try:
        bet = int(args[1])
    except ValueError:
        await update.message.reply_text("❗ Bet must be a whole number.")
        return

    if bet <= 0:
        await update.message.reply_text("❗ Bet must be positive.")
        return
    if data["balance"] < bet:
        await update.message.reply_text("🚫 Not enough balance for this bet.")
        return

    roll = random.randint(1, 6)
    result = "even" if roll % 2 == 0 else "odd"

    if result == choice:
        # win: net +bet; we implement by adding +bet to playable and +bet to withdrawable
        data["balance"] += bet
        data["withdrawable"] += bet
        await update.message.reply_text(
            f"🎲 You guessed **{choice.upper()}**.\n"
            f"🎯 Roll: **{roll}** ({result.upper()})\n"
            f"✅ You WON! Net gain: **₱{bet}**\n\n"
            f"{get_balances_text(user_id)}"
        )
    else:
        data["balance"] -= bet
        await update.message.reply_text(
            f"🎲 You guessed **{choice.upper()}**.\n"
            f"🎯 Roll: **{roll}** ({result.upper()})\n"
            f"❌ You LOST **₱{bet}** (deducted from playable)\n\n"
            f"{get_balances_text(user_id)}"
        )


# ==========================
# SCATTER SPIN (SLOTS) with ANIMATION
# ==========================
async def scatterspin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Usage: /scatterspin 50
    3 same = 5x bet (net +4x)
    2 same = 2x bet (net +1x)
    no match = -bet (playable)
    Winnings add to withdrawable too.
    """
    user_id = update.effective_user.id
    data = ensure_user(user_id)

    args = context.args
    if len(args) != 1:
        await update.message.reply_text(
            "🎰 **ScatterSpin – Slot Machine**\n"
            "Format: `/scatterspin 50`\n"
            "• 3️⃣ same symbols = **5× bet**\n"
            "• 2️⃣ same symbols = **2× bet**\n"
            "• ❌ No match = **lose bet**\n"
            "• **Winnings** add to **withdrawable**."
        )
        return

    try:
        bet = int(args[0])
    except ValueError:
        await update.message.reply_text("❗ Bet must be a whole number.")
        return

    if bet <= 0:
        await update.message.reply_text("❗ Bet must be positive.")
        return
    if data["balance"] < bet:
        await update.message.reply_text("🚫 Not enough balance for this bet.")
        return

    symbols = ["🍒", "7️⃣", "⭐", "💎"]
    reels = [random.choice(symbols) for _ in range(3)]

    # send an animated-like sequence by editing the same message a few times
    placeholder = ["⬜", "⬜", "⬜"]
    msg = await update.message.reply_text(f"🎰 {' '.join(placeholder)}\nSpinning...")
    await asyncio.sleep(0.5)
    for i in range(3):
        placeholder[i] = random.choice(symbols)
        await asyncio.sleep(0.6)
        await msg.edit_text(f"🎰 {' '.join(placeholder)}\nSpinning...")

    # final result
    result = reels
    await asyncio.sleep(0.5)
    await msg.edit_text(f"🎰 {' '.join(result)}")

    # evaluate
    if result[0] == result[1] == result[2]:
        win = bet * 5
        data["balance"] += win
        data["withdrawable"] += win
        outcome = f"🎉 **JACKPOT!** 3 in a row → +₱{win}"
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        win = bet * 2
        data["balance"] += win
        data["withdrawable"] += win
        outcome = f"✨ Nice! 2 matched → +₱{win}"
    else:
        data["balance"] -= bet
        outcome = f"❌ No match → -₱{bet} (playable)"

    await update.message.reply_text(f"{outcome}\n\n{get_balances_text(user_id)}")


# ==========================
# WIRE-UP & POLLING
# ==========================
def main():
    app = Application.builder().token(TOKEN).build()

    # Core commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("withdraw", withdraw))

    # Earning & invites
    app.add_handler(CommandHandler("captcha2earn", captcha2earn))
    app.add_handler(CommandHandler("invite", invite))

    # Games
    app.add_handler(CommandHandler("dice", dice))
    app.add_handler(CommandHandler("scatterspin", scatterspin))

    # Captcha answer handler (any text when a captcha is pending)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_captcha_text))

    print("Bot is running...")
    app.run_polling()  # perfect for Render Free plan (Background Worker)

if __name__ == "__main__":
    main()
