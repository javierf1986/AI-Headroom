from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _as_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _as_path(value: str | None, default_relative: str) -> str:
    base_dir = Path(__file__).resolve().parents[2]
    raw_value = value if value is not None else default_relative
    path = Path(raw_value)
    if not path.is_absolute():
        path = base_dir / path
    return str(path.resolve())


@dataclass(slots=True)
class Settings:
    ollama_api_url: str = os.getenv("OLLAMA_API_URL", "http://localhost:11434/v1")
    preferred_model_keyword: str = os.getenv("LLM_PREFERRED_MODEL", "mistral")
    tts_provider: str = os.getenv("TTS_PROVIDER", "edge")
    default_voice_en: str = os.getenv("TTS_VOICE_EN", "en-US-AriaNeural")
    default_voice_es: str = os.getenv("TTS_VOICE_ES", "es-MX-DaliaNeural")
    artifact_dir: str = _as_path(os.getenv("AUDIO_ARTIFACT_DIR"), "artifacts/audio")
    backend_host: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    backend_port: int = _as_int(os.getenv("BACKEND_PORT"), 8000)
    frontend_port: int = _as_int(os.getenv("FRONTEND_PORT"), 5173)
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/ai_assistant",
    )
    default_client_id: str = os.getenv("DEFAULT_CLIENT_ID", "local-default")


settings = Settings()
