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

