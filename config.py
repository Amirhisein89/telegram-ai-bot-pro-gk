import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

SUBSCRIPTION_DAYS = 7

DB_NAME = "bot_database.db"
