from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CameraFrame:
    data: bytes
    captured_at: datetime
    sensor_timestamp_ns: int
    controls: dict[str, Any]


@dataclass(frozen=True)
class CapturedPair:
    rgb: CameraFrame
    nir: CameraFrame
    profile_id: str

    @property
    def sync_delta_ms(self) -> float:
        return abs(self.rgb.sensor_timestamp_ns - self.nir.sensor_timestamp_ns) / 1_000_000


@dataclass(frozen=True)
class QueueItem:
    capture_id: str
    path: Path
    manifest: dict[str, Any]

    @property
    def rgb_path(self) -> Path:
        return self.path / "rgb.jpg"

    @property
    def nir_path(self) -> Path:
        return self.path / "nir.jpg"
