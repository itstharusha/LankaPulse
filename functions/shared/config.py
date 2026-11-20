"""Environment-backed local configuration for the LankaPulse pipeline."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("LANKAPULSE_ENV", "local")
    timezone: str = os.getenv("LANKAPULSE_TIMEZONE", "Asia/Colombo")
    raw_root: Path = Path(os.getenv("LANKAPULSE_RAW_ROOT", "data/raw"))
    cleansed_root: Path = Path(os.getenv("LANKAPULSE_CLEANSED_ROOT", "data/cleansed"))
    curated_root: Path = Path(os.getenv("LANKAPULSE_CURATED_ROOT", "data/curated"))
    quarantine_root: Path = Path(os.getenv("LANKAPULSE_QUARANTINE_ROOT", "data/quarantine"))


settings = Settings()