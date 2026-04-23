from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import sqlite3
from datetime import datetime, timedelta

TOKEN = "8630304004:AAF6p2xJhPBd5KxKD1rEIf4vgISjhWtByYQ"

conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    type TEXT
)
""")
conn.commit()

ACTION_TYPES = {
    "new_message": "💬 Личное сообщение",
    "like": "👍 Лайк",
    "new_comment": "📢 Комментарий",
    "repost": "🔁 Репост",
    "my_post": "✍️ Пост",
    "follow_request": "➕ Подписка"
}

def main_menu():
    buttons = [
        [InlineKeyboardButton("💬", callback_data="new_message"),
         InlineKeyboardButton("👍", callback_data="like")],
        [InlineKeyboardButton("📢", callback_data="new_comment"),
         InlineKeyboardButton("🔁", callback_data="repost")],
        [InlineKeyboardButton("✍️", callback_data="my_post"),
         InlineKeyboardButton("➕", callback_data="follow_request")],
        [InlineKeyboardButton("📊 Сегодня", callback_data="stats")],
        [InlineKeyboardButton("⏪ Отменить", callback_data="undo")],
        [InlineKeyboardButton("📈 Неделя", callback_data="week")]
    ]
    return InlineKeyboardMarkup(buttons)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выбери действие:", reply_markup=main_menu())

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    today = datetime.now().strftime("%Y-%m-%d")

    if query.data in ACTION_TYPES:
        cursor.execute("INSERT INTO actions (date, type) VALUES (?, ?)", (today, query.data))
        conn.commit()
        await query.edit_message_text(f"Добавлено: {ACTION_TYPES[query.data]}", reply_markup=main_menu())

    elif query.data == "stats":
        cursor.execute("SELECT type, COUNT(*) FROM actions WHERE date=? GROUP BY type", (today,))
        rows = cursor.fetchall()

        total = sum(r[1] for r in rows)
        text = f"📊 Сегодня: {total}\n\n"

        for t, c in rows:
            text += f"{ACTION_TYPES[t]}: {c}\n"

        await query.edit_message_text(text, reply_markup=main_menu())

    elif query.data == "undo":
        cursor.execute("SELECT id FROM actions WHERE date=? ORDER BY id DESC LIMIT 1", (today,))
        row = cursor.fetchone()

        if row:
            cursor.execute("DELETE FROM actions WHERE id=?", (row[0],))
            conn.commit()
            text = "Последнее действие удалено"
        else:
            text = "Нечего удалять"

        await query.edit_message_text(text, reply_markup=main_menu())

    elif query.data == "week":
        text = "📈 ОТЧЁТ ЗА НЕДЕЛЮ\n\n"
        total_week = 0
        type_totals = {}

        for i in range(7):
            day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            cursor.execute("SELECT type, COUNT(*) FROM actions WHERE date=? GROUP BY type", (day,))
            rows = cursor.fetchall()

            day_total = sum(r[1] for r in rows)
            total_week += day_total

            text += f"{day}: {day_total}\n"

            for t, c in rows:
                type_totals[t] = type_totals.get(t, 0) + c

        text += f"\n🔥 ИТОГО: {total_week}\n\n📋 По типам:\n"

        for t, c in type_totals.items():
            text += f"{ACTION_TYPES[t]}: {c}\n"

        await query.edit_message_text(text, reply_markup=main_menu())

async def reminder(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("SELECT COUNT(*) FROM actions WHERE date=?", (today,))
    total = cursor.fetchone()[0]

    text = f"🌙 Итог за {today}\n\nСегодня: {total}"

    await context.bot.send_message(chat_id, text)

async def start_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.job_queue.run_daily(reminder, time=datetime.strptime("21:00", "%H:%M").time(), chat_id=chat_id)

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle))
    app.add_handler(CommandHandler("remind", start_reminder))

    app.run_polling()

if __name__ == "__main__":
    main()