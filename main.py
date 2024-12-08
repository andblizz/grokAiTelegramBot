import os
import json
import logging
from pathlib import Path
from telegram import Update, ForceReply
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
import openai

# Инициализация логгера
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Чтение токена телеграм бота из переменной окружения
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
if not TELEGRAM_BOT_TOKEN:
    logger.error("Необходимо установить TELEGRAM_BOT_TOKEN в переменных окружения.")
    exit(1)

# Путь к файлу с пользовательскими данными
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
USER_DATA_FILE = DATA_DIR / "user_data.json"


# Функция загрузки данных
def load_user_data():
    if USER_DATA_FILE.exists():
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# Функция сохранения данных
def save_user_data(data):
    with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


user_data = load_user_data()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот для общения с Grok AI.\n\n"
        "Сначала тебе нужно установить свой API ключ xAI. Используй команду:\n"
        "/setkey <твой_ключ>"
    )


async def setkey_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Пожалуйста, укажи ключ после команды. Пример: /setkey my_secret_key_here")
        return

    key = " ".join(args).strip()
    user_id = str(update.message.from_user.id)
    user_data[user_id] = {
        "api_key": key
    }
    save_user_data(user_data)
    await update.message.reply_text(
        "Ключ успешно сохранен! Теперь просто напиши мне сообщение, и я передам его в Grok.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in user_data or "api_key" not in user_data[user_id]:
        await update.message.reply_text(
            "У тебя еще не установлен ключ! Используй /setkey <твой_ключ> для его установки."
        )
        return

    user_message = update.message.text
    user_api_key = user_data[user_id]["api_key"]

    client = OpenAI(
        api_key=user_api_key,
        base_url="https://api.x.ai/v1",
    )

    try:
        response = client.chat.completions.create(
            model="grok-beta",
            messages=[{"role": "user", "content": user_message}],
            max_tokens=300,
            temperature=0.7
        )
        answer = response.choices[0].message.content.strip()
        await update.message.reply_text(answer)
    except openai.APIError as e:
        logger.error(f"Grok вернул ошибку API: {e}")
        await update.message.reply_text(f"Grok вернул ошибку API. Попробуйте заменить API ключ командой /setkey:\n{e}")


def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("setkey", setkey_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()


if __name__ == "__main__":
    main()
