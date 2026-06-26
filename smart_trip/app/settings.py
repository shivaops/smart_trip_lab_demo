"""
app/settings.py
----------------
Purpose:
- Central place for application configuration
- Other Python files IMPORT values from here

Why needed:
- Avoid hardcoding values everywhere
"""

from dataclasses import dataclass
import os
from dotenv import load_dotenv

# Reads .env file and loads variables into environment
load_dotenv()

@dataclass(frozen=True)
class Settings:
    """
    This class holds configuration values.

    frozen=True means:
    - Values cannot be changed accidentally at runtime
    """

    # Application title shown in browser & UI
    APP_NAME: str = os.getenv(
        "APP_NAME",
        "Smart Trip API — AI Travel Assistant Portal"
    )

    # Server host
    HOST: str = os.getenv("HOST", "127.0.0.1")

    # Server port
    PORT: int = int(os.getenv("PORT", "8001"))


# Create ONE shared settings object
settings = Settings()
