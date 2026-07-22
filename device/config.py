from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AgentConfig:
    device_id: str
    api_base_url: str
    device_key: str
    queue_path: Path
    registration_file: Path | None
    simulate: bool
    rgb_camera_index: int
    nir_camera_index: int
    poll_seconds: float
    profile_refresh_seconds: float
    heartbeat_seconds: float
    retry_base_seconds: float
    retry_max_seconds: float
    capture_retry_count: int
    capture_on_start: bool
    align_to_interval: bool
    simulated_illuminance_lux: float
    verify_tls: bool
    firmware_version: str

    @classmethod
    def load(cls, path: str | Path) -> "AgentConfig":
        config_path = Path(path).resolve()
        raw: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))
        base = config_path.parent

        def resolve_optional(value: str | None) -> Path | None:
            if not value:
                return None
            candidate = Path(value)
            return candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()

        queue_value = Path(str(raw.get("queue_path", "./queue")))
        queue_path = (
            queue_value.resolve()
            if queue_value.is_absolute()
            else (base / queue_value).resolve()
        )
        return cls(
            device_id=str(raw["device_id"]),
            api_base_url=os.getenv(
                "FIELDSCOPE_API_URL",
                str(raw.get("api_base_url", "http://127.0.0.1:8000")),
            ).rstrip("/"),
            device_key=os.getenv(
                "FIELDSCOPE_DEVICE_KEY",
                str(raw.get("device_key", "")),
            ),
            queue_path=queue_path,
            registration_file=resolve_optional(raw.get("registration_file")),
            simulate=bool(raw.get("simulate", False)),
            rgb_camera_index=int(raw.get("rgb_camera_index", 0)),
            nir_camera_index=int(raw.get("nir_camera_index", 1)),
            poll_seconds=max(1.0, float(raw.get("poll_seconds", 5))),
            profile_refresh_seconds=max(
                5.0,
                float(raw.get("profile_refresh_seconds", 60)),
            ),
            heartbeat_seconds=max(5.0, float(raw.get("heartbeat_seconds", 60))),
            retry_base_seconds=max(1.0, float(raw.get("retry_base_seconds", 5))),
            retry_max_seconds=max(5.0, float(raw.get("retry_max_seconds", 300))),
            capture_retry_count=max(0, int(raw.get("capture_retry_count", 1))),
            capture_on_start=bool(raw.get("capture_on_start", False)),
            align_to_interval=bool(raw.get("align_to_interval", True)),
            simulated_illuminance_lux=max(
                0.0,
                float(raw.get("simulated_illuminance_lux", 7500)),
            ),
            verify_tls=bool(raw.get("verify_tls", True)),
            firmware_version=str(raw.get("firmware_version", "0.2.0")),
        )
