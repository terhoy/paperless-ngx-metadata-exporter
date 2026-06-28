from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
import secrets
from typing import Any

APP_VERSION = "1.0.2"


@dataclass(frozen=True)
class AppConfig:
    base_url: str = ""
    api_token: str = ""
    secret_key: str = ""
    host: str = "0.0.0.0"
    port: int = 5001
    default_language: str = "nb"
    config_path: str = "/data/config.json"
    metadata_ttl_seconds: int = 300
    request_timeout_seconds: int = 20
    max_export_pages: int = 200
    demo_mode: bool = False
    basic_auth_enabled: bool = False
    basic_auth_user: str = "admin"
    basic_auth_password: str = ""

    @staticmethod
    def _bool(value: str | None, default: bool = False) -> bool:
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    @classmethod
    def from_env(cls) -> "AppConfig":
        config_path = os.getenv("APP_CONFIG_PATH", "/data/config.json")
        file_data: dict[str, Any] = {}
        try:
            p = Path(config_path)
            if p.exists() and p.read_text(encoding="utf-8").strip():
                file_data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            file_data = {}

        return cls(
            base_url=(os.getenv("PAPERLESS_BASE_URL") or file_data.get("base_url") or "").rstrip("/"),
            api_token=os.getenv("PAPERLESS_API_TOKEN") or file_data.get("api_token") or "",
            secret_key=os.getenv("APP_SECRET_KEY") or file_data.get("secret_key") or secrets.token_urlsafe(32),
            host=os.getenv("APP_HOST", "0.0.0.0"),
            port=int(os.getenv("APP_PORT", "5001")),
            default_language=os.getenv("APP_DEFAULT_LANGUAGE", file_data.get("default_language", "nb")),
            config_path=config_path,
            metadata_ttl_seconds=int(os.getenv("APP_METADATA_TTL_SECONDS", "300")),
            request_timeout_seconds=int(os.getenv("APP_REQUEST_TIMEOUT_SECONDS", "20")),
            max_export_pages=int(os.getenv("APP_MAX_EXPORT_PAGES", "200")),
            demo_mode=cls._bool(os.getenv("APP_DEMO_MODE"), False),
            basic_auth_enabled=cls._bool(os.getenv("APP_BASIC_AUTH_ENABLED"), False),
            basic_auth_user=os.getenv("APP_BASIC_AUTH_USER", "admin"),
            basic_auth_password=os.getenv("APP_BASIC_AUTH_PASSWORD", ""),
        )

    def save_local(self, base_url: str, api_token: str, default_language: str = "nb") -> None:
        path = Path(self.config_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "base_url": base_url.rstrip("/"),
            "api_token": api_token,
            "default_language": default_language,
            "secret_key": self.secret_key,
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
