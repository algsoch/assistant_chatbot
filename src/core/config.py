"""
Application Configuration
Centralized settings for TDS Assistant
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application settings loaded from environment variables"""
    
    # App Info
    APP_NAME: str = "TDS Assistant"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "AI-Powered Question Answering System for Data Science"
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    STATIC_DIR: Path = BASE_DIR / "static"
    TEMPLATES_DIR: Path = BASE_DIR / "templates"
    UPLOADS_DIR: Path = BASE_DIR / "uploads"
    
    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Webhooks
    DISCORD_WEBHOOK: str = os.getenv("DISCORD_WEBHOOK", "")
    SLACK_WEBHOOK: str = os.getenv("SLACK_WEBHOOK", "")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    
    # Notification Settings
    NOTIF_INTERVAL_SECONDS: int = int(os.getenv("NOTIF_INTERVAL_SECONDS", "300"))
    
    # CORS
    CORS_ORIGINS: list = ["*"]
    
    @classmethod
    def ensure_directories(cls):
        """Create required directories if they don't exist"""
        for directory in [cls.STATIC_DIR, cls.TEMPLATES_DIR, cls.UPLOADS_DIR]:
            directory.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
