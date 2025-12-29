import os
from dotenv import load_dotenv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # config.py -> app/ -> parent
env_path = PROJECT_ROOT / "config.env"
load_dotenv(dotenv_path=env_path)

print("env path = ", env_path)

# JWT & cookie settings
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
SECURE_COOKIES = os.getenv("SECURE_COOKIES", "True").lower() in ["true", "1", "yes"]
MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", "5"))
LOCK_TIME_MINUTES = int(os.getenv("LOCK_TIME_MINUTES", "1"))
TEST_MODE = os.getenv("TEST", "false").lower() == "true"
CORS_URL = os.getenv("CORS_URL")

print("MAX_ATTEMPTS =", MAX_ATTEMPTS)
print("LOCK_TIME_MINUTES =", LOCK_TIME_MINUTES)
print("reading config file")