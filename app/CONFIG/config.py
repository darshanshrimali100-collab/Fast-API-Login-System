import os
from dotenv import load_dotenv
from pathlib import Path

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
master_db = str(BASE_DIR / "database.sqlite3")

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # config.py -> app/ -> parent
load_dotenv()

# JWT & cookie settings
SECRET_KEY = os.getenv("SECRET_KEY")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 600))
SECURE_COOKIES = os.getenv("SECURE_COOKIES", "True").lower() in ["true", "1", "yes"]
MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", "5"))
LOCK_TIME_MINUTES = int(os.getenv("LOCK_TIME_MINUTES", "1"))
TEST_MODE = os.getenv("TEST", "false").lower() == "true"
CORS_URL = os.getenv("CORS_URL")
SMTP_MAIL = os.getenv("SMTP_MAIL")
SMTP_PWD = os.getenv("SMTP_PWD")
master_db = os.getenv("DB_PATH")
DATA_FOLDER = os.getenv("DATA_FOLDER")

print("MAX_ATTEMPTS =", MAX_ATTEMPTS)
print("LOCK_TIME_MINUTES =", LOCK_TIME_MINUTES)
print("reading config file")