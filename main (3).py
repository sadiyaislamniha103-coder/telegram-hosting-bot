import os
import time
import subprocess
import psutil
import sys
import zipfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# ============ CONFIGURATION ============
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # ✅ Render ENV

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not found in environment variables")

BASE_DIR = os.path.abspath("uploads")
LOG_DIR = os.path.abspath("logs")
os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

START_TIME = time.time()
user_processes = {}
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

    for iid, data in processes.items():
        buttons.append([
            InlineKeyboardButton(
                f"🛑 Stop {data['file']} (ID: {iid})",
                callback_data=f"{user_id}::stop::{iid}"
            )
        ])

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

# ============ HANDLERS ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **Multi-Hosting Bot**\n\nUpload & run your scripts easily 🚀",
        reply_markup=reply_menu(),
        parse_mode="Markdown"
    )

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    if text == "📤 Upload File":
        await update.message.reply_text("📎 Send (.py / .js / .sh / .zip)")

    elif text == "📂 My Scripts":
        await update.message.reply_text(
            "📂 **Control Panel:**",
            reply_markup=scripts_menu(user_id),
            parse_mode="Markdown"
        )

    elif text == "📊 Statistics":
        uptime = int(time.time() - START_TIME)
        active = len(user_processes.get(user_id, {}))
        await update.message.reply_text(
            f"⏱ Uptime: {uptime}s\n🚀 Active Scripts: {active}"
        )

    elif text == "📈 Live Resource Monitor":
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        await update.message.reply_text(
            f"🧠 CPU: `{cpu}%`\n💾 RAM: `{ram}%`",
            parse_mode="Markdown"
        )

    elif text == "📞 Contact Owner":
        await update.message.reply_text("👤 Owner: @Samiulislamd")

async def upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc:
        return

    user_id = update.message.from_user.id
    fname = doc.file_name

    if not fname.endswith(('.py', '.js', '.sh', '.zip')):
        await update.message.reply_text("❌ Invalid file type")
        return

    user_dir = os.path.join(BASE_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    save_path = os.path.join(user_dir, fname)

    file = await doc.get_file()
    await file.download_to_drive(save_path)

    if fname.endswith('.zip'):
        with zipfile.ZipFile(save_path, 'r') as z:
            z.extractall(user_dir)
        os.remove(save_path)
        await update.message.reply_text("✅ ZIP extracted")
    else:
        await update.message.reply_text(f"✅ `{fname}` uploaded", parse_mode="Markdown")

# ============ CALLBACK ============
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global instance_counter
    q = update.callback_query
    await q.answer()

    try:
        user_id, action, param = q.data.split("::")
        user_id = int(user_id)
    except:
        return

    processes = user_processes.setdefault(user_id, {})
    user_dir = os.path.join(BASE_DIR, str(user_id))

    if action == "run":
        path = os.path.join(user_dir, param)

        if param.endswith('.py'):
            cmd = [sys.executable, path]
        elif param.endswith('.js'):
            cmd = ["node", path]
        elif param.endswith('.sh'):
            cmd = ["bash", path]
        else:
            return

        instance_counter += 1
        log_path = os.path.join(LOG_DIR, f"{user_id}_{instance_counter}.log")
        log = open(log_path, "a")

        proc = subprocess.Popen(cmd, cwd=user_dir, stdout=log, stderr=log)
        processes[instance_counter] = {"file": param, "proc": proc}

        await q.edit_message_text(
            f"✅ Running `{param}` (ID {instance_counter})",
            parse_mode="Markdown",
            reply_markup=scripts_menu(user_id)
        )

    elif action == "stop":
        iid = int(param)
        p = processes.pop(iid, None)
        if p:
            p["proc"].terminate()
            await q.edit_message_text(
                "🛑 Script stopped",
                reply_markup=scripts_menu(user_id)
            )

    elif action == "delfile":
        path = os.path.join(user_dir, param)
        if os.path.exists(path):
            os.remove(path)
        await q.edit_message_text(
            "🗑️ File deleted",
            reply_markup=scripts_menu(user_id)
        )

# ============ MAIN ============
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, upload_file))
    app.add_handler(CallbackQueryHandler(buttons))

    print("🤖 Bot running on Render...")
    app.run_polling()

if __name__ == "__main__":
    main()