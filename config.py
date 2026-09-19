import os

# Токен бота — берётся из переменной окружения BOT_TOKEN,
# либо вставь его напрямую вместо "ВСТАВЬ_СЮДА_ТОКЕН" ниже.
# Получить токен: написать @BotFather в Telegram -> /newbot
BOT_TOKEN = os.getenv("BOT_TOKEN", "8937575412:AAHszy77zv-uz5ufA3LlLH13a_hGVZKAD7o")

if not BOT_TOKEN or BOT_TOKEN == "ВСТАВЬ_СЮДА_ТОКЕН":
    raise ValueError(
        "BOT_TOKEN не задан! Укажи его в переменной окружения BOT_TOKEN "
        "или впиши прямо в config.py вместо 'ВСТАВЬ_СЮДА_ТОКЕН'."
    )

# Telegram ID владельца бота — только у него есть доступ к админ-панели
ADMIN_ID = 7237651575

# Возрастные ограничения анкет
MIN_AGE = 12
MAX_AGE = 26

# Путь к файлу базы данных SQLite
DB_PATH = os.path.join(os.path.dirname(__file__), "dating_bot.db")

# Длительность буста анкеты (в часах) за один "прогон" из админки
BOOST_DURATION_HOURS = 48
