from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HeartbeatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = "online"
    wifi_ssid: str | None = None
    wifi_rssi_dbm: float | None = None
    ip_address: str | None = None
    firmware_version: str | None = None
    queue_depth: int = Field(default=0, ge=0)
    storage_used_percent: float = Field(default=0, ge=0, le=100)
    battery_percent: float | None = Field(default=None, ge=0, le=100)


class CaptureProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    calibration_id: str = Field(min_length=1, max_length=120)
    capture_interval_minutes: int = Field(ge=10, le=30)
    profile: dict[str, Any]

