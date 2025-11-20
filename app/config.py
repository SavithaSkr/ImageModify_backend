import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE", "60")))

    # Automation server URL (same VPS OR local)
    AUTOMATION_API_URL: str = os.getenv("AUTOMATION_API_URL")

settings = Settings()
