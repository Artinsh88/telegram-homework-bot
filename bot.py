import os
import csv
import pandas as pd
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

TOKEN = os.environ.get("7826136781:AAGESNdUORoMolYAfK9SidodzXQkurp6xsQ")
ADMIN_USERNAME = "Akingshah"

USERS_FILE = "users.csv"
HW_FILE = "homework.csv"

def init_files():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["user_id", "name", "grade"])

    if not os.path.exists(HW_FILE):
        with open(HW_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(
                ["user_id", "name", "grade", "date", "time", "weekday", "status"]
            )

def get_user_info(user_id):
    try:
        with open(USERS_FILE, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["user_id"] == str(user_id):
                    return r
    except FileNotFoundError:
        init_files()
    return None

def already_sent(user_id, date_str):
    try:
        with open(HW_FILE, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["user_id"] == str(user_id) and r["date"] == date_str:
                    return True
    except FileNotFoundError:
        init_files()
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 🌸\n"
        "نام و نام خانوادگی + مقطع رو بفرست\n"
        "مثال:\n"
        "علی احمدی - هفتم\n\n"
        "بعد از ثبت‌نام، می‌تونی عکس تکلیف رو هر روز بفرستی."
    )

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if get_user_info(user_id):
        await update.message.reply_text("✅ شما قبلاً ثبت‌نام کردید")
        return

    text = update.message.text.strip()
    if "-" not in text:
        await update.message.reply_text("❗ فرمت صحیح: نام - مقطع\nمثال: علی احمدی - هفتم")
        return

    name, grade = [x.strip() for x in text.split("-", 1)]

    with open(USERS_FILE, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([str(user_id), name, grade])

    await update.message.reply_text(f"✅ ثبت‌نام انجام شد\n👤 نام: {name}\n🎓 مقطع: {grade}")

async def receive_hw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    info = get_user_info(user.id)

    if not info:
        await update.message.reply_text("❗ اول اسمت رو بفرست (مثل: علی احمدی - هفتم)")
        return

    if not (update.message.photo or update.message.document):
        await update.message.reply_text("❌ لطفاً عکس یا فایل تکلیف رو بفرست")
        return

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    weekday = now.strftime("%A")

    days_fa = {
        "Saturday": "شنبه",
        "Sunday": "یکشنبه",
        "Monday": "دوشنبه",
        "Tuesday": "سه‌شنبه",
        "Wednesday": "چهارشنبه",
        "Thursday": "پنجشنبه",
        "Friday": "جمعه"
    }
    weekday_fa = days_fa.get(weekday, weekday)

    if weekday == "Friday":
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        if already_sent(user.id, yesterday):
            await update.message.reply_text(
                "❌ پنجشنبه ارسال کردی، جمعه نمی‌تونی ارسال کنی"
            )
            return

    if already_sent(user.id, date_str):
        await update.message.reply_text("❌ امروز قبلاً تکلیف فرستادی")
        return

    status = "به‌موقع"
    time_str = now.strftime("%H:%M:%S")

    with open(HW_FILE, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            str(user.id),
            info["name"],
            info["grade"],
            date_str,
            time_str,
            weekday_fa,
            status
        ])

    await update.message.reply_text(
        f"✅ تکلیف ثبت شد\n"
        f"📅 تاریخ: {date_str}\n"
        f"⏰ ساعت: {time_str}\n"
        f"📚 مقطع: {info['grade']}"
    )

async def report(update: Update, c

ontext: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ دسترسی نداری")
        return

    try:
        df = pd.read_csv(HW_FILE, encoding="utf-8")

        if df.empty:
            await update.message.reply_text("📭 هیچ تکلیفی ثبت نشده")
            return

        text = "📊 گزارش تکالیف:\n\n"
        for name, group in df.groupby("name"):
            grade = group.iloc[0]["grade"]
            text += f"👤 {name} ({grade}): {len(group)} بار\n"

        text += f"\n✅ مجموع: {len(df)} تکلیف"
        await update.message.reply_text(text)

        excel_file = "report.xlsx"
        df.to_excel(excel_file, index=False, encoding="utf-8")

        with open(excel_file, "rb") as f:
            await update.message.reply_document(f, filename="گزارش_تکالیف.xlsx")

    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")

async def my_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    info = get_user_info(user_id)

    if not info:
        await update.message.reply_text("❗ اول ثبت‌نام کن")
        return

    try:
        df = pd.read_csv(HW_FILE, encoding="utf-8")
        user_hw = df[df["user_id"] == str(user_id)]

        count = len(user_hw)
        last_date = user_hw["date"].iloc[-1] if count > 0 else "ثبت نشده"

        await update.message.reply_text(
            f"👤 نام: {info['name']}\n"
            f"🎓 مقطع: {info['grade']}\n"
            f"📊 تعداد تکالیف ارسالی: {count}\n"
            f"📅 آخرین ارسال: {last_date}"
        )
    except:
        await update.message.reply_text(
            f"👤 نام: {info['name']}\n"
            f"🎓 مقطع: {info['grade']}\n"
            f"📊 تعداد تکالیف ارسالی: 0"
        )

def main():
    print("🤖 در حال راه‌اندازی ربات...")
    init_files()

    if not TOKEN:
        print("❌ خطا: TOKEN پیدا نشد!")
        print("✅ در Railway: Variables → TOKEN را اضافه کن")
        return

    try:
        app = Application.builder().token(TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("report", report))
        app.add_handler(CommandHandler("mystatus", my_status))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, register))
        app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, receive_hw))

        print("✅ ربات راه‌اندازی شد")
        print("⏳ در حال اتصال به تلگرام...")

        app.run_polling()

    except Exception as e:
        print(f"❌ خطا در اجرای ربات: {e}")
        print("ℹ️  ممکن است توکن نامعتبر باشد")

if __name__ == "__main__":
    main()

