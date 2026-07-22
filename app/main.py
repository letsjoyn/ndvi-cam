from __future__ import annotations

import json
import mimetypes
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .config import Settings
from .database import Database
from .image_processing import (
    ImageValidationError,
    compute_ndvi,
    make_thumbnail,
    sha256_bytes,
    validate_pair,
)
from .models import Capture, Device, utcnow
from .schemas import CaptureProfileUpdate, HeartbeatIn
from .seed import seed_demo_data
from .storage import Storage, build_storage


def parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="captured_at must be ISO 8601") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def media_url(key: str | None) -> str | None:
    return f"/api/media/{quote(key, safe='/')}" if key else None


def json_load(raw: str, fallback: Any) -> Any:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return fallback


def serialize_device(device: Device) -> dict[str, Any]:
    return {
        "id": device.id,
        "name": device.name,
        "site_name": device.site_name,
        "status": device.status,
        "last_seen_at": device.last_seen_at.isoformat() + "Z"
        if device.last_seen_at
        else None,
        "wifi_ssid": device.wifi_ssid,
        "wifi_rssi_dbm": device.wifi_rssi_dbm,
        "ip_address": device.ip_address,
        "firmware_version": device.firmware_version,
        "calibration_id": device.calibration_id,
        "capture_interval_minutes": device.capture_interval_minutes,
        "queue_depth": device.queue_depth,
        "storage_used_percent": device.storage_used_percent,
        "battery_percent": device.battery_percent,
        "latitude": device.latitude,
        "longitude": device.longitude,
    }


def serialize_capture(capture: Capture, include_metadata: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": capture.id,
        "device_id": capture.device_id,
        "device_name": capture.device.name if capture.device else capture.device_id,
        "site_name": capture.device.site_name if capture.device else "",
        "captured_at": capture.captured_at.isoformat() + "Z",
        "date_key": capture.date_key,
        "source": capture.source,
        "status": capture.status,
        "quality_state": capture.quality_state,
        "quality_flags": json_load(capture.quality_flags_json, []),
        "sync_delta_ms": capture.sync_delta_ms,
        "resolution": {
            "width": capture.rgb_width,
            "height": capture.rgb_height,
        },
        "quality": {
            "rgb_blur_score": round(capture.rgb_blur_score, 2),
            "nir_blur_score": round(capture.nir_blur_score, 2),
            "rgb_mean": round(capture.rgb_mean, 4),
            "nir_mean": round(capture.nir_mean, 4),
            "saturated_fraction": round(capture.saturated_fraction, 5),
        },
        "ndvi": {
            "mean": round(capture.mean_ndvi, 4),
            "minimum": round(capture.min_ndvi, 4),
            "maximum": round(capture.max_ndvi, 4),
            "healthy_fraction": round(capture.healthy_fraction, 4),
            "stressed_fraction": round(capture.stressed_fraction, 4),
            "bare_fraction": round(capture.bare_fraction, 4),
        },
        "assets": {
            "rgb": media_url(capture.rgb_key),
            "nir": media_url(capture.nir_key),
            "ndvi": media_url(capture.ndvi_key),
            "ndvi_data": media_url(capture.ndvi_data_key),
            "rgb_thumb": media_url(capture.rgb_thumb_key),
            "nir_thumb": media_url(capture.nir_thumb_key),
            "ndvi_thumb": media_url(capture.ndvi_thumb_key),
        },
        "hashes": {
            "rgb_sha256": capture.rgb_sha256,
            "nir_sha256": capture.nir_sha256,
        },
    }
    if include_metadata:
        payload["metadata"] = json_load(capture.metadata_json, {})
    return payload


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings.from_env()
    app_settings.data_dir.mkdir(parents=True, exist_ok=True)
    database = Database(app_settings.database_url)
    storage = build_storage(app_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database.create_all()
        if app_settings.seed_demo:
            with database.session_factory() as db:
                seed_demo_data(db, storage)
        yield

    app = FastAPI(
        title=f"{app_settings.app_name} API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = app_settings
    app.state.database = database
    app.state.storage = storage

    def get_db() -> Session:
        with database.session_factory() as db:
            yield db

    app.mount(
        "/static",
        StaticFiles(directory=app_settings.static_dir),
        name="static",
    )

    @app.get("/", include_in_schema=False)
    def dashboard() -> FileResponse:
        return FileResponse(app_settings.static_dir / "index.html")

    @app.get("/api/health")
    def health(db: Session = Depends(get_db)) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": app_settings.app_name,
            "devices": db.scalar(select(func.count(Device.id))) or 0,
            "captures": db.scalar(select(func.count(Capture.id))) or 0,
            "storage_backend": app_settings.storage_backend,
            "time": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/api/dashboard")
    def dashboard_data(days: int = 14, db: Session = Depends(get_db)) -> dict[str, Any]:
        days = min(max(days, 1), 90)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        start = now - timedelta(days=days - 1)
        captures = list(
            db.scalars(
                select(Capture)
                .options(selectinload(Capture.device))
                .where(Capture.captured_at >= start)
                .order_by(Capture.captured_at.desc())
            )
        )
        devices = list(db.scalars(select(Device).order_by(Device.name)))
        today_key = now.date().isoformat()
        today = [capture for capture in captures if capture.date_key == today_key]
        accepted = [capture for capture in captures if capture.status == "accepted"]
        pass_count = sum(capture.quality_state == "pass" for capture in captures)

        grouped: dict[str, list[Capture]] = defaultdict(list)
        for capture in captures:
            grouped[capture.date_key].append(capture)
        trend = []
        for key in sorted(grouped):
            items = grouped[key]
            trend.append(
                {
                    "date": key,
                    "mean_ndvi": round(
                        sum(item.mean_ndvi for item in items) / len(items),
                        4,
                    ),
                    "healthy_fraction": round(
                        sum(item.healthy_fraction for item in items) / len(items),
                        4,
                    ),
                    "captures": len(items),
                }
            )

        return {
            "summary": {
                "captures_today": len(today),
                "mean_ndvi": round(
                    sum(item.mean_ndvi for item in accepted) / len(accepted),
                    4,
                )
                if accepted
                else None,
                "quality_pass_rate": round(pass_count / len(captures), 4)
                if captures
                else None,
                "online_devices": sum(device.status == "online" for device in devices),
                "total_devices": len(devices),
                "queued_uploads": sum(device.queue_depth for device in devices),
            },
            "trend": trend,
            "latest": [
                serialize_capture(capture)
                for capture in sorted(
                    captures,
                    key=lambda item: item.captured_at,
                    reverse=True,
                )[:8]
            ],
            "devices": [serialize_device(device) for device in devices],
        }

    @app.get("/api/devices")
    def list_devices(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
        return [
            serialize_device(device)
            for device in db.scalars(select(Device).order_by(Device.name))
        ]

    @app.get("/api/devices/{device_id}/capture-profile")
    def get_capture_profile(
        device_id: str,
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        device = db.get(Device, device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        return {
            "device_id": device.id,
            "calibration_id": device.calibration_id,
            "capture_interval_minutes": device.capture_interval_minutes,
            "profile": json_load(device.profile_json, {}),
            "ingest": {
                "method": "POST",
                "path": "/api/captures",
                "device_key_header": "X-Device-Key",
                "content_type": "multipart/form-data",
            },
            "updated_at": device.updated_at.isoformat() + "Z",
        }

    @app.put("/api/devices/{device_id}/capture-profile")
    def update_capture_profile(
        device_id: str,
        payload: CaptureProfileUpdate,
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        device = db.get(Device, device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        device.calibration_id = payload.calibration_id
        device.capture_interval_minutes = payload.capture_interval_minutes
        device.profile_json = json.dumps(payload.profile, separators=(",", ":"))
        device.updated_at = utcnow()
        db.commit()
        return get_capture_profile(device_id, db)

    @app.post("/api/devices/{device_id}/heartbeat")
    def device_heartbeat(
        device_id: str,
        payload: HeartbeatIn,
        x_device_key: str | None = Header(default=None),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        verify_device_key(app_settings, x_device_key)
        device = db.get(Device, device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        for field, value in payload.model_dump(exclude_none=True).items():
            setattr(device, field, value)
        device.last_seen_at = utcnow()
        device.updated_at = utcnow()
        db.commit()
        return serialize_device(device)

    @app.get("/api/captures")
    def list_captures(
        date_from: date | None = None,
        date_to: date | None = None,
        device_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        db: Session = Depends(get_db),
    ) -> list[dict[str, Any]]:
        query = select(Capture).options(selectinload(Capture.device))
        if date_from:
            query = query.where(Capture.date_key >= date_from.isoformat())
        if date_to:
            query = query.where(Capture.date_key <= date_to.isoformat())
        if device_id:
            query = query.where(Capture.device_id == device_id)
        if status:
            query = query.where(Capture.status == status)
        query = query.order_by(Capture.captured_at.desc()).limit(min(max(limit, 1), 500))
        return [serialize_capture(capture) for capture in db.scalars(query)]

    @app.get("/api/captures/{capture_id}")
    def get_capture(
        capture_id: str,
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        capture = db.scalar(
            select(Capture)
            .options(selectinload(Capture.device))
            .where(Capture.id == capture_id)
        )
        if not capture:
            raise HTTPException(status_code=404, detail="Capture not found")
        return serialize_capture(capture, include_metadata=True)

    @app.post("/api/captures")
    async def create_capture(
        device_id: str = Form(...),
        captured_at: str | None = Form(default=None),
        source: str = Form(default="device"),
        sync_delta_ms: float | None = Form(default=None),
        metadata: str = Form(default="{}"),
        rgb: UploadFile = File(...),
        nir: UploadFile = File(...),
        x_device_key: str | None = Header(default=None),
        db: Session = Depends(get_db),
    ) -> JSONResponse:
        if source == "device":
            verify_device_key(app_settings, x_device_key)
        if source not in {"device", "manual"}:
            raise HTTPException(status_code=422, detail="source must be device or manual")

        device = db.get(Device, device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        rgb_data = await read_upload(rgb, app_settings.max_upload_mb)
        nir_data = await read_upload(nir, app_settings.max_upload_mb)
        try:
            metadata_payload = json.loads(metadata or "{}")
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail="metadata must be valid JSON") from exc
        if not isinstance(metadata_payload, dict):
            raise HTTPException(status_code=422, detail="metadata must be a JSON object")

        profile = json_load(device.profile_json, {})
        try:
            rgb_metrics, nir_metrics, flags = validate_pair(
                rgb_data,
                nir_data,
                profile,
                strict_resolution=source == "device",
                sync_delta_ms=sync_delta_ms,
                metadata=metadata_payload if source == "device" else {},
            )
            ndvi = compute_ndvi(
                rgb_data,
                nir_data,
                profile.get("ndvi_calibration"),
            )
        except ImageValidationError as exc:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "IMAGE_QUALITY_REJECTED",
                    "message": str(exc),
                },
            ) from exc

        capture_time = parse_datetime(captured_at)
        capture_id = str(uuid.uuid4())
        date_key = capture_time.date().isoformat()
        prefix = f"captures/{date_key}/{capture_id}"
        keys = {
            "rgb": f"{prefix}/rgb.jpg",
            "nir": f"{prefix}/nir.jpg",
            "ndvi": f"{prefix}/ndvi.png",
            "ndvi_data": f"{prefix}/ndvi-data.npz",
            "rgb_thumb": f"{prefix}/rgb-thumb.jpg",
            "nir_thumb": f"{prefix}/nir-thumb.jpg",
            "ndvi_thumb": f"{prefix}/ndvi-thumb.jpg",
        }

        written: list[str] = []
        try:
            writes = [
                (keys["rgb"], rgb_data, rgb.content_type or "image/jpeg"),
                (keys["nir"], nir_data, nir.content_type or "image/jpeg"),
                (keys["ndvi"], ndvi.heatmap_png, "image/png"),
                (keys["ndvi_data"], ndvi.data_npz, "application/octet-stream"),
                (keys["rgb_thumb"], make_thumbnail(rgb_data), "image/jpeg"),
                (keys["nir_thumb"], make_thumbnail(nir_data), "image/jpeg"),
                (keys["ndvi_thumb"], make_thumbnail(ndvi.heatmap_png), "image/jpeg"),
            ]
            for key, data, content_type in writes:
                storage.put_bytes(key, data, content_type)
                written.append(key)

            capture = Capture(
                id=capture_id,
                device_id=device_id,
                captured_at=capture_time,
                date_key=date_key,
                source=source,
                status="accepted",
                quality_state="warning" if flags else "pass",
                sync_delta_ms=sync_delta_ms,
                rgb_key=keys["rgb"],
                nir_key=keys["nir"],
                ndvi_key=keys["ndvi"],
                ndvi_data_key=keys["ndvi_data"],
                rgb_thumb_key=keys["rgb_thumb"],
                nir_thumb_key=keys["nir_thumb"],
                ndvi_thumb_key=keys["ndvi_thumb"],
                rgb_width=rgb_metrics.width,
                rgb_height=rgb_metrics.height,
                rgb_blur_score=rgb_metrics.blur_score,
                nir_blur_score=nir_metrics.blur_score,
                rgb_mean=rgb_metrics.mean_normalized,
                nir_mean=nir_metrics.mean_normalized,
                saturated_fraction=max(
                    rgb_metrics.saturated_fraction,
                    nir_metrics.saturated_fraction,
                ),
                mean_ndvi=ndvi.mean,
                min_ndvi=ndvi.minimum,
                max_ndvi=ndvi.maximum,
                healthy_fraction=ndvi.healthy_fraction,
                stressed_fraction=ndvi.stressed_fraction,
                bare_fraction=ndvi.bare_fraction,
                quality_flags_json=json.dumps(flags),
                metadata_json=json.dumps(metadata_payload),
                rgb_sha256=sha256_bytes(rgb_data),
                nir_sha256=sha256_bytes(nir_data),
            )
            db.add(capture)
            device.last_seen_at = utcnow()
            if source == "device":
                device.status = "online"
            db.commit()
            db.refresh(capture)
            capture.device = device
        except Exception:
            db.rollback()
            for key in written:
                storage.delete(key)
            raise

        return JSONResponse(
            status_code=201,
            content=serialize_capture(capture, include_metadata=True),
        )

    @app.post("/api/captures/{capture_id}/recompute-ndvi")
    def recompute_ndvi(
        capture_id: str,
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        capture = db.scalar(
            select(Capture)
            .options(selectinload(Capture.device))
            .where(Capture.id == capture_id)
        )
        if not capture:
            raise HTTPException(status_code=404, detail="Capture not found")
        profile = json_load(capture.device.profile_json, {})
        try:
            ndvi = compute_ndvi(
                storage.get_bytes(capture.rgb_key),
                storage.get_bytes(capture.nir_key),
                profile.get("ndvi_calibration"),
            )
        except ImageValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        storage.put_bytes(capture.ndvi_key, ndvi.heatmap_png, "image/png")
        if capture.ndvi_data_key:
            storage.put_bytes(
                capture.ndvi_data_key,
                ndvi.data_npz,
                "application/octet-stream",
            )
        storage.put_bytes(
            capture.ndvi_thumb_key,
            make_thumbnail(ndvi.heatmap_png),
            "image/jpeg",
        )
        capture.mean_ndvi = ndvi.mean
        capture.min_ndvi = ndvi.minimum
        capture.max_ndvi = ndvi.maximum
        capture.healthy_fraction = ndvi.healthy_fraction
        capture.stressed_fraction = ndvi.stressed_fraction
        capture.bare_fraction = ndvi.bare_fraction
        db.commit()
        return serialize_capture(capture, include_metadata=True)

    @app.get("/api/media/{key:path}")
    def get_media(key: str) -> StreamingResponse:
        try:
            data = storage.get_bytes(key)
        except (FileNotFoundError, ValueError):
            raise HTTPException(status_code=404, detail="Media not found")
        content_type = mimetypes.guess_type(Path(key).name)[0] or "application/octet-stream"
        return StreamingResponse(
            BytesIO(data),
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )

    return app


def verify_device_key(settings: Settings, provided: str | None) -> None:
    if settings.device_ingest_key and provided != settings.device_ingest_key:
        raise HTTPException(status_code=401, detail="Invalid device key")


async def read_upload(upload: UploadFile, maximum_mb: int) -> bytes:
    data = await upload.read()
    if not data:
        raise HTTPException(status_code=422, detail=f"{upload.filename} is empty")
    if len(data) > maximum_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"{upload.filename} exceeds the {maximum_mb} MB limit",
        )
    return data


app = create_app()

