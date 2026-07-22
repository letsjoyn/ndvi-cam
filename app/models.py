from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    site_name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="offline", nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    wifi_ssid: Mapped[str | None] = mapped_column(String(120), nullable=True)
    wifi_rssi_dbm: Mapped[float | None] = mapped_column(Float, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    firmware_version: Mapped[str] = mapped_column(String(80), default="unknown")
    calibration_id: Mapped[str] = mapped_column(String(120), nullable=False)
    capture_interval_minutes: Mapped[int] = mapped_column(Integer, default=15)
    queue_depth: Mapped[int] = mapped_column(Integer, default=0)
    storage_used_percent: Mapped[float] = mapped_column(Float, default=0.0)
    battery_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    profile_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    captures: Mapped[list["Capture"]] = relationship(
        back_populates="device",
        cascade="all, delete-orphan",
    )


class Capture(Base):
    __tablename__ = "captures"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    date_key: Mapped[str] = mapped_column(String(10), index=True)
    source: Mapped[str] = mapped_column(String(20), default="device")
    status: Mapped[str] = mapped_column(String(30), default="accepted", index=True)
    quality_state: Mapped[str] = mapped_column(String(30), default="pass")
    sync_delta_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    rgb_key: Mapped[str] = mapped_column(Text, nullable=False)
    nir_key: Mapped[str] = mapped_column(Text, nullable=False)
    ndvi_key: Mapped[str] = mapped_column(Text, nullable=False)
    ndvi_data_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    rgb_thumb_key: Mapped[str] = mapped_column(Text, nullable=False)
    nir_thumb_key: Mapped[str] = mapped_column(Text, nullable=False)
    ndvi_thumb_key: Mapped[str] = mapped_column(Text, nullable=False)

    rgb_width: Mapped[int] = mapped_column(Integer)
    rgb_height: Mapped[int] = mapped_column(Integer)
    rgb_blur_score: Mapped[float] = mapped_column(Float)
    nir_blur_score: Mapped[float] = mapped_column(Float)
    rgb_mean: Mapped[float] = mapped_column(Float)
    nir_mean: Mapped[float] = mapped_column(Float)
    saturated_fraction: Mapped[float] = mapped_column(Float)

    mean_ndvi: Mapped[float] = mapped_column(Float)
    min_ndvi: Mapped[float] = mapped_column(Float)
    max_ndvi: Mapped[float] = mapped_column(Float)
    healthy_fraction: Mapped[float] = mapped_column(Float)
    stressed_fraction: Mapped[float] = mapped_column(Float)
    bare_fraction: Mapped[float] = mapped_column(Float)

    quality_flags_json: Mapped[str] = mapped_column(Text, default="[]")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    rgb_sha256: Mapped[str] = mapped_column(String(64))
    nir_sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    device: Mapped[Device] = relationship(back_populates="captures")


class DeviceCommand(Base):
    __tablename__ = "device_commands"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    command_type: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class WebcamSnapshot(Base):
    __tablename__ = "webcam_snapshots"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    date_key: Mapped[str] = mapped_column(String(10), index=True)
    image_key: Mapped[str] = mapped_column(Text, nullable=False)
    thumb_key: Mapped[str] = mapped_column(Text, nullable=False)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    fps: Mapped[float] = mapped_column(Float)
    zoom: Mapped[float] = mapped_column(Float)
    blur_score: Mapped[float] = mapped_column(Float)
    mean_normalized: Mapped[float] = mapped_column(Float)
    dark_fraction: Mapped[float] = mapped_column(Float)
    saturated_fraction: Mapped[float] = mapped_column(Float)
    camera_name: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class DevicePreview(Base):
    __tablename__ = "device_previews"

    device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.id"),
        primary_key=True,
    )
    session_id: Mapped[str] = mapped_column(String(80), nullable=False)
    requested_until: Mapped[datetime] = mapped_column(DateTime, index=True)
    interval_seconds: Mapped[float] = mapped_column(Float, default=2.0)
    preview_width: Mapped[int] = mapped_column(Integer, default=960)
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    latest_session_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    latest_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rgb_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    nir_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sync_delta_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    rgb_blur_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    nir_blur_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rgb_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    nir_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    rgb_saturated_fraction: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    nir_saturated_fraction: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )
