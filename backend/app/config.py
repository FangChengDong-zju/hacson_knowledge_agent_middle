from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass(frozen=True)
class Settings:
    app_name: str = _env("APP_NAME", "Hacson Knowledge Agent")
    app_env: str = _env("APP_ENV", "local")
    textbook_dir: Path = Path(_env("TEXTBOOK_DIR", "E:/textbooks"))
    cached_chunks_path: Path = Path(
        _env(
            "CACHED_CHUNKS_PATH",
            str(PROJECT_ROOT.parent / "health_agent_demo" / "data" / "textbook_chunks.jsonl"),
        )
    )
    cached_stats_path: Path = Path(
        _env(
            "CACHED_STATS_PATH",
            str(PROJECT_ROOT.parent / "health_agent_demo" / "reports" / "textbook_index_stats.json"),
        )
    )
    frontend_origin: str = _env("FRONTEND_ORIGIN", "http://localhost:5173")
    data_dir: Path = PROJECT_ROOT / "data"
    demo_dir: Path = PROJECT_ROOT / "data" / "demo"
    upload_dir: Path = PROJECT_ROOT / "data" / "uploads"
    processed_dir: Path = PROJECT_ROOT / "data" / "processed"
    index_dir: Path = PROJECT_ROOT / "data" / "indexes"
    report_dir: Path = PROJECT_ROOT / "report"
    llm_api_key: str = _env("LLM_API_KEY")
    llm_base_url: str = _env("LLM_BASE_URL")
    llm_model: str = _env("LLM_MODEL")
    llm_wire_api: str = _env("LLM_WIRE_API", "chat")


settings = Settings()


def ensure_runtime_dirs() -> None:
    for path in (settings.data_dir, settings.demo_dir, settings.upload_dir, settings.processed_dir, settings.index_dir, settings.report_dir):
        path.mkdir(parents=True, exist_ok=True)
