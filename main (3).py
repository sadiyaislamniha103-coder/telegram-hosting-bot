
import os
import time
import subprocess
import psutil
import sys
import zipfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# ============ CONFIGURATION ============
BOT_TOKEN = "8355745493:AAEaUrfvkHCNOBRkFONMUlwuO142lgpeRfI" 

BASE_DIR = os.path.abspath("uploads")
LOG_DIR = os.path.abspath("logs")
os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

START_TIME = time.time()
user_processes = {}  # {user_id: {instance_id: {...}} }
instance_counter = 0

# ============ KEYBOARD MENU ============
def reply_menu():
    return ReplyKeyboardMarkup(
        [["📤 Upload File", "📂 My Scripts"],
         ["📊 Statistics", "📈 Live Resource Monitor"],
         ["📞 Contact Owner"]],
        resize_keyboard=True
    )

def scripts_menu(user_id):
    buttons = []
    processes = user_processes.get(user_id, {})
    
    # Running scripts
    for iid, data in processes.items():
        buttons.append([InlineKeyboardButton(f"🛑 Stop {data['file']} (ID: {iid})", callback_data=f"{user_id}::stop::{iid}")])
    
    # User folder files
    user_dir = os.path.join(BASE_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    files = [f for f in os.listdir(user_dir) if f.endswith(('.py', '.js', '.sh'))]
    
    for fname in files:
        buttons.append([
            InlineKeyboardButton(f"▶️ Run {fname}", callback_data=f"{user_id}::run::{fname}"),
            InlineKeyboardButton(f"🗑️ Delete", callback_data=f"{user_id}::delfile::{fname}")
        ])
    
    if not buttons:
        buttons.append([InlineKeyboardButton("❌ No scripts found", callback_data="noop")])
    return InlineKeyboardMarkup(buttons)

# ============ HANDLER FUNCTIONS ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **Multi-Hosting Bot**\n\nSamiul Hosting Bot is a Telegram bot that makes managing your hosting and servers easy. With simple commands, you can check server status, create backups, view hosting plans, and get real-time notifications. It’s designed to save time and simplify server management for everyone! 🚀", 
        reply_markup=reply_menu(), 
        parse_mode="Markdown"
    )

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    
    if text == "📤 Upload File":
        await update.message.reply_text("📎 Please send the file ( .py / .js / .sh / .zip )")
    
    elif text == "📂 My Scripts":
        await update.message.reply_text("📂 **Control Panel:**", reply_markup=scripts_menu(user_id), parse_mode="Markdown")
    
    elif text == "📊 Statistics":
        uptime = int(time.time() - START_TIME)
        active_scripts = len(user_processes.get(user_id, {}))
        await update.message.reply_text(f"⏱ Uptime: {uptime}s\n🚀 Your Active Scripts: {active_scripts}")
    
    elif text == "📈 Live Resource Monitor":
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        running_scripts = len(user_processes.get(user_id, {}))
        await update.message.reply_text(
            f"📈 **System Monitor**\n\n🧠 CPU: `{cpu}%`\n💾 RAM: `{ram}%` \n🚀 Your Running Scripts: `{running_scripts}`",
            parse_mode="Markdown"
        )
    
    elif text == "📞 Contact Owner":
        await update.message.reply_text("👤 Owner: @Samiulislamd")

async def upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc: return
    user_id = update.message.from_user.id
    
    fname = doc.file_name
    if not fname.endswith(('.py', '.js', '.sh', '.zip')):
        await update.message.reply_text("❌ Invalid file format!")
        return
    
    user_dir = os.path.join(BASE_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    save_path = os.path.join(user_dir, fname)
    
    file = await doc.get_file()
    await file.download_to_drive(save_path)
    
    if fname.endswith('.zip'):
        try:
            with zipfile.ZipFile(save_path, 'r') as z:
                z.extractall(user_dir)
            os.remove(save_path)
            await update.message.reply_text("✅ ZIP file has been extracted!")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    else:
        await update.message.reply_text(f"✅ `{fname}` uploaded successfully!", parse_mode="Markdown")

# ============ BUTTON ACTIONS ============
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global instance_counter, user_processes
    q = update.callback_query
    data = q.data

    if data == "noop":
        await q.answer("Nothing to do here", show_alert=False)
        return

    try:
        user_id_str, action, param = data.split("::")
        user_id = int(user_id_str)
    except ValueError:
        await q.answer("❌ Invalid data", show_alert=True)
        return

    processes = user_processes.setdefault(user_id, {})
    user_dir = os.path.join(BASE_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)

    # Run script
    if action == "run":
        fname = param
        path = os.path.join(user_dir, fname)

        if fname.endswith('.py'):
            cmd = [sys.executable, path]
        elif fname.endswith('.js'):
            cmd = ['node', path]
        elif fname.endswith('.sh'):
            cmd = ['bash', path]
        else:
            await q.answer("❌ Invalid format", show_alert=True)
            return

        instance_counter += 1
        log_path = os.path.join(LOG_DIR, f"{user_id}_{fname}_{instance_counter}.log")
        
        try:
            log_file = open(log_path, "a", buffering=1)
            proc = subprocess.Popen(
                cmd, cwd=user_dir, stdout=log_file, stderr=log_file, 
                start_new_session=True
            )
            processes[instance_counter] = {"file": fname, "proc": proc, "log": log_path}
            
            await q.answer(f"🚀 {fname} started!", show_alert=False) 
            await q.edit_message_text(
                f"✅ **Bot Running!**\n📄 File: `{fname}`\n🆔 ID: `{instance_counter}`",
                parse_mode="Markdown",
                reply_markup=scripts_menu(user_id)
            )
        except Exception as e:
            await q.answer(f"❌ Error: {str(e)}", show_alert=True)

    # Stop script
    elif action == "stop":
        iid = int(param)
        pdata = processes.pop(iid, None)
        if pdata:
            pdata["proc"].terminate()
            await q.answer(f"🛑 {pdata['file']} stopped", show_alert=False)
            await q.edit_message_text("📂 **Control panel updated:**", reply_markup=scripts_menu(user_id))
        else:
            await q.answer("⚠️ Script not running", show_alert=False)

    # Delete file
    elif action == "delfile":
        fname = param
        path = os.path.join(user_dir, fname)

        # Stop if running
        for iid, pdata in list(processes.items()):
            if pdata["file"] == fname:
                pdata["proc"].kill()
                processes.pop(iid)

        if os.path.exists(path):
            os.remove(path)
            await q.answer(f"🗑️ {fname} deleted", show_alert=False)
            await q.edit_message_text("📂 **File removed**", reply_markup=scripts_menu(user_id))
        else:
            await q.answer("❌ File not found", show_alert=True)

# ============ MAIN FUNCTION ============
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, upload_file))
    app.add_handler(CallbackQueryHandler(buttons))
    
    print("🤖 Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
