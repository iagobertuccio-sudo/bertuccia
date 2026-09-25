import os
from dotenv import load_dotenv

load_dotenv()

# Banco de dados
DATABASE_URL = os.getenv("DATABASE_URL")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

# APIs esportivas
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
ODDS_API_KEY     = os.getenv("ODDS_API_KEY")
SPORTMONKS_KEY   = os.getenv("SPORTMONKS_KEY")
