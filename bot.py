import logging
import asyncio
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================================
#  SOZLAMALAR — shu yerni o'zgartiring
# ============================================================
BOT_TOKEN = "8662923508:AAFd6GWguvxwlsDEUleQ1vEtkcVfLfyXBIo"   # @BotFather dan olingan token
ADMIN_ID   = 8225902523              # Sizning Telegram ID ingiz

# ============================================================
#  YORDAMCHI FUNKSIYALAR
# ============================================================
def rf(a, b):   return round(random.uniform(a, b), 2)
def ri(a, b):   return random.randint(a, b)

def get_risk_emoji(coeff):
    if coeff < 2.0:   return "🟢", "PAST"
    if coeff < 4.0:   return "🟡", "O'RTA"
    return "🔴", "YUQORI"

def format_time():
    return datetime.now().strftime("%H:%M:%S")

# ============================================================
#  SIGNAL GENERATORLARI
# ============================================================
def signal_random() -> dict:
    entry  = rf(1.05, 1.30)
    exit_  = rf(1.40, 9.00)
    conf   = ri(55, 88)
    emoji, risk = get_risk_emoji(exit_)
    return dict(
        strategy="🎲 Tasodifiy",
        entry=entry, exit=exit_, conf=conf,
        risk_emoji=emoji, risk=risk,
        tip=f"x{entry} dan keyin kiring, x{exit_} da CHIQING!",
        extra=""
    )

def signal_martingale(prev_bet: float = 1.0, is_loss: bool = False) -> dict:
    bet    = round(prev_bet * 2, 2) if is_loss else prev_bet
    exit_  = rf(1.50, 3.50)
    conf   = ri(60, 85)
    emoji, risk = get_risk_emoji(exit_)
    return dict(
        strategy="📈 Martingale",
        entry=1.10, exit=exit_, conf=conf,
        risk_emoji=emoji, risk=risk,
        tip=f"x1.10 da kiring, x{exit_} da oling!",
        extra=f"💰 Tavsiya stavka: ${bet}  (yutqazsangiz ${round(bet*2,2)} qiling)"
    )

def signal_stats() -> dict:
    entry  = rf(1.10, 1.25)
    exit_  = rf(1.30, 2.50)
    conf   = ri(68, 95)
    emoji, risk = get_risk_emoji(exit_)
    return dict(
        strategy="📊 Statistika",
        entry=entry, exit=exit_, conf=conf,
        risk_emoji=emoji, risk=risk,
        tip=f"Konservativ: x{entry} kiring, x{exit_} da xavfsiz chiqish!",
        extra=f"📉 Oxirgi 10 raunddan {ri(6,9)} tasi ushbu diapazondan o'tdi"
    )

def signal_supercharged() -> dict:
    """Yuqori koeffitsient — yuqori risk"""
    entry  = rf(1.20, 1.50)
    exit_  = rf(4.00, 15.00)
    conf   = ri(35, 65)
    return dict(
        strategy="🚀 Super Signal",
        entry=entry, exit=exit_, conf=conf,
        risk_emoji="🔴", risk="YUQORI",
        tip=f"x{entry} da kiring, x{exit_} JACKPOT!",
        extra="⚠️ Yuqori risk! Kichik stavka tavsiya etiladi"
    )

def build_signal_text(sig: dict) -> str:
    bar_len = int(sig['conf'] / 10)
    bar = "█" * bar_len + "░" * (10 - bar_len)
    return (
        f"✈️  *AVIATOR SIGNAL*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📍 Strategiya: *{sig['strategy']}*\n"
        f"⏰ Vaqt: `{format_time()}`\n\n"
        f"🛫 Kirish nuqtasi:  *x{sig['entry']}*\n"
        f"🛬 Chiqish nuqtasi: *x{sig['exit']}*\n\n"
        f"📊 Ishonch:  `{bar}` *{sig['conf']}%*\n"
        f"{sig['risk_emoji']} Risk darajasi: *{sig['risk']}*\n\n"
        f"💡 _{sig['tip']}_\n"
        + (f"\n{sig['extra']}\n" if sig['extra'] else "")
        + f"━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ _Ehtiyotkorlik bilan o'ynang!_"
    )

# ============================================================
#  /start
# ============================================================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("✈️ Signal olish", callback_data="menu_signal")],
        [
            InlineKeyboardButton("🎲 Tasodifiy",    callback_data="sig_random"),
            InlineKeyboardButton("📈 Martingale",   callback_data="sig_martingale"),
        ],
        [
            InlineKeyboardButton("📊 Statistika",   callback_data="sig_stats"),
            InlineKeyboardButton("🚀 Super Signal", callback_data="sig_super"),
        ],
        [InlineKeyboardButton("📋 Oxirgi signallar", callback_data="history")],
        [InlineKeyboardButton("❓ Yordam",           callback_data="help")],
    ]
    await update.message.reply_text(
        "✈️ *Aviator Signal Bot*\n\n"
        "Salom! Men sizga Aviator o'yini uchun signal beraman.\n\n"
        "*Strategiyalar:*\n"
        "🎲 Tasodifiy — har xil signallar\n"
        "📈 Martingale — yutqazganda 2x stavka\n"
        "📊 Statistika — xavfsiz, konservativ\n"
        "🚀 Super Signal — yuqori koeff, yuqori risk\n\n"
        "Quyidan tanlang 👇",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ============================================================
#  SIGNAL CALLBACK
# ============================================================
# Global history (xotira)
signal_history: list[dict] = []

async def handle_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⏳ Tahlil qilinmoqda...")

    kind = query.data  # sig_random | sig_martingale | sig_stats | sig_super

    # Loading
    await query.edit_message_text("⏳ *Signal tahlil qilinmoqda...*\n\n`▓▓▓▓░░░░░░`", parse_mode="Markdown")
    await asyncio.sleep(0.8)
    await query.edit_message_text("⏳ *Signal tahlil qilinmoqda...*\n\n`▓▓▓▓▓▓▓░░░`", parse_mode="Markdown")
    await asyncio.sleep(0.7)

    # Generate
    if kind == "sig_random":
        sig = signal_random()
    elif kind == "sig_martingale":
        sig = signal_martingale()
    elif kind == "sig_stats":
        sig = signal_stats()
    else:
        sig = signal_supercharged()

    # Save to history
    signal_history.insert(0, sig)
    if len(signal_history) > 10:
        signal_history.pop()

    kb = [
        [InlineKeyboardButton("🔄 Yangi signal", callback_data=kind)],
        [
            InlineKeyboardButton("🎲 Tasodifiy",  callback_data="sig_random"),
            InlineKeyboardButton("📈 Martingale", callback_data="sig_martingale"),
        ],
        [
            InlineKeyboardButton("📊 Statistika", callback_data="sig_stats"),
            InlineKeyboardButton("🚀 Super",      callback_data="sig_super"),
        ],
        [InlineKeyboardButton("🏠 Bosh menyu",   callback_data="back_main")],
    ]
    await query.edit_message_text(
        build_signal_text(sig),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ============================================================
#  HISTORY
# ============================================================
async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not signal_history:
        text = "📋 *Oxirgi signallar*\n\nHali signal olinmagan."
    else:
        lines = ["📋 *Oxirgi signallar*\n"]
        for i, s in enumerate(signal_history[:5], 1):
            lines.append(
                f"{i}. {s['strategy']} — *x{s['exit']}* "
                f"({s['conf']}% ishonch) {s['risk_emoji']}"
            )
        text = "\n".join(lines)

    kb = [[InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")]]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

# ============================================================
#  HELP
# ============================================================
async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "❓ *Yordam*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "*Buyruqlar:*\n"
        "/start — Asosiy menyu\n"
        "/signal — Tezkor signal\n\n"
        "*Strategiyalar:*\n"
        "🎲 *Tasodifiy* — har safar boshqacha signal\n"
        "📈 *Martingale* — yutqazganda stavkani 2x\n"
        "📊 *Statistika* — xavfsiz, past risk\n"
        "🚀 *Super Signal* — yuqori koeff, yuqori risk\n\n"
        "*Signal tushuntirish:*\n"
        "🛫 Kirish — qaysi koeffda bet bosing\n"
        "🛬 Chiqish — qaysi koeffda cash out qiling\n"
        "📊 Ishonch — signalning ehtimolligi\n\n"
        "⚠️ _Kazino o'yinlari tasodifiy. Hech qanday "
        "signal 100% kafolat bermaydi!_"
    )
    kb = [[InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")]]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

# ============================================================
#  BACK / MENU
# ============================================================
async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = [
        [InlineKeyboardButton("✈️ Signal olish", callback_data="menu_signal")],
        [
            InlineKeyboardButton("🎲 Tasodifiy",    callback_data="sig_random"),
            InlineKeyboardButton("📈 Martingale",   callback_data="sig_martingale"),
        ],
        [
            InlineKeyboardButton("📊 Statistika",   callback_data="sig_stats"),
            InlineKeyboardButton("🚀 Super Signal", callback_data="sig_super"),
        ],
        [InlineKeyboardButton("📋 Oxirgi signallar", callback_data="history")],
        [InlineKeyboardButton("❓ Yordam",           callback_data="help")],
    ]
    await query.edit_message_text(
        "✈️ *Aviator Signal Bot*\n\nStrategiyani tanlang 👇",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ============================================================
#  /signal — tezkor buyruq
# ============================================================
async def cmd_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sig = signal_random()
    kb = [
        [InlineKeyboardButton("🔄 Yangi signal", callback_data="sig_random")],
        [InlineKeyboardButton("🏠 Menyu",        callback_data="back_main")],
    ]
    await update.message.reply_text(
        build_signal_text(sig),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ============================================================
#  MAIN
# ============================================================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("signal", cmd_signal))

    # Callbacks
    app.add_handler(CallbackQueryHandler(handle_signal, pattern="^sig_(random|martingale|stats|super)$"))
    app.add_handler(CallbackQueryHandler(show_history,  pattern="^history$"))
    app.add_handler(CallbackQueryHandler(show_help,     pattern="^help$"))
    app.add_handler(CallbackQueryHandler(back_main,     pattern="^back_main$"))
    app.add_handler(CallbackQueryHandler(back_main,     pattern="^menu_signal$"))

    print("✅ Aviator Signal Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()


