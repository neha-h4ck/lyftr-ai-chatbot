import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    llm_api_keys: list[str]
    model: str
    database_url: str
    allowed_origins: list[str]
    enable_failure_simulation: bool
    default_system_prompt: str

def _csv_env(name: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]

settings = Settings(
    llm_api_keys=_csv_env("LLM_API_KEYS"),
    model=os.getenv("LLM_MODEL", "gemini/gemini-2.5-flash"),
    database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./app.db"),
    allowed_origins=_csv_env("ALLOWED_ORIGINS") or ["http://localhost:3000"],
    enable_failure_simulation=os.getenv("ENABLE_FAILURE_SIMULATION", "false").lower() == "true",
    default_system_prompt=os.getenv(
        "DEFAULT_SYSTEM_PROMPT",
        "You are a helpful, accurate assistant. If you are unsure, say so."
    ),
)
