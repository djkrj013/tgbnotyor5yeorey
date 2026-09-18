import os

# Токен бота — берётся из переменной окружения BOT_TOKEN.
# Получить токен: написать @BotFather в Telegram -> /newbot
BOT_TOKEN = os.getenv("BOT_TOKEN", "8422336740:AAHpu30LS_mIOTXeOnIisfUmF2IlykNsmxM")

# Telegram ID владельца бота — только у него есть доступ к админ-панели
ADMIN_ID = 7237651575

# Возрастные ограничения анкет
MIN_AGE = 12
MAX_AGE = 26

# Путь к файлу базы данных SQLite
DB_PATH = os.path.join(os.path.dirname(__file__), "dating_bot.db")

# Длительность буста анкеты (в часах) за один "прогон" из админки
BOOST_DURATION_HOURS = 48
