from __future__ import annotations

from typing import Any, Literal

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


class DeviceCommandCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["capture_now"]
    payload: dict[str, Any] = Field(default_factory=dict)


class DeviceCommandComplete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "failed"]
    capture_id: str | None = Field(default=None, max_length=80)
    message: str | None = Field(default=None, max_length=500)


class WebcamConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: Literal[640, 1280, 1920]
    height: Literal[480, 720, 1080]
    fps: Literal[10, 15, 30]
    zoom: float = Field(ge=1.0, le=3.0)


class DevicePreviewStart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interval_seconds: float = Field(default=2.0, ge=1.0, le=10.0)
    preview_width: int = Field(default=960, ge=320, le=1280)
    session_seconds: int = Field(default=90, ge=30, le=300)
