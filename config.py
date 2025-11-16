import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
SSL="/certs/root.crt"
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Формируем строку подключения к MySQL
SQLALCHEMY_DATABASE_URI = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:3306/{DB_NAME}"
)
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Если сертификат указан — добавляем SSL
SQLALCHEMY_ENGINE_OPTIONS = {
    "connect_args": {
        "ssl": {"ca": SSL}
    }
} if SSL else {}
