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
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from .config import Settings
from .database import Database
from .image_processing import (
    ImageMetrics,
    ImageValidationError,
    analyze_image,
    compute_ndvi,
    make_thumbnail,
    sha256_bytes,
    validate_pair,
)
from .models import (
    Capture,
    Device,
    DeviceCommand,
    DevicePreview,
    WebcamSnapshot,
    utcnow,
)
from .schemas import (
    CaptureProfileUpdate,
    DeviceCommandComplete,
    DeviceCommandCreate,
    DevicePreviewStart,
    HeartbeatIn,
    WebcamConfigUpdate,
)
from .seed import seed_demo_data
from .storage import Storage, build_storage
from .webcam import WebcamError, WebcamManager


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


def serialize_command(command: DeviceCommand) -> dict[str, Any]:
    return {
        "id": command.id,
        "device_id": command.device_id,
        "type": command.command_type,
        "status": command.status,
        "payload": json_load(command.payload_json, {}),
        "result": json_load(command.result_json, {}),
        "created_at": command.created_at.isoformat() + "Z",
        "claimed_at": command.claimed_at.isoformat() + "Z"
        if command.claimed_at
        else None,
        "completed_at": command.completed_at.isoformat() + "Z"
        if command.completed_at
        else None,
    }


def serialize_webcam_snapshot(snapshot: WebcamSnapshot) -> dict[str, Any]:
    return {
        "id": snapshot.id,
        "captured_at": snapshot.captured_at.isoformat() + "Z",
        "date_key": snapshot.date_key,
        "camera_name": snapshot.camera_name,
        "resolution": {
            "width": snapshot.width,
            "height": snapshot.height,
        },
        "fps": round(snapshot.fps, 2),
        "zoom": round(snapshot.zoom, 2),
        "quality": {
            "blur_score": round(snapshot.blur_score, 2),
            "mean": round(snapshot.mean_normalized, 4),
            "dark_fraction": round(snapshot.dark_fraction, 5),
            "saturated_fraction": round(snapshot.saturated_fraction, 5),
        },
        "assets": {
            "rgb": media_url(snapshot.image_key),
            "thumb": media_url(snapshot.thumb_key),
        },
    }


def webcam_quality_failures(metrics: ImageMetrics) -> list[str]:
    failures: list[str] = []
    if metrics.blur_score < 80.0:
        failures.append(
            f"Image is too blurry (sharpness {metrics.blur_score:.1f}; minimum 80.0)"
        )
    if metrics.mean_normalized < 0.06:
        failures.append("Image is too dark")
    if metrics.mean_normalized > 0.94:
        failures.append("Image is overexposed")
    if metrics.dark_fraction > 0.45:
        failures.append("Dark-pixel fraction is too high")
    if metrics.saturated_fraction > 0.20:
        failures.append("Saturated-pixel fraction is too high")
    return failures


def serialize_device_preview(
    preview: DevicePreview | None,
    device: Device,
) -> dict[str, Any]:
    now = utcnow()
    if preview is None:
        return {
            "device_id": device.id,
            "device_name": device.name,
            "site_name": device.site_name,
            "active": False,
            "state": "stopped",
            "session_id": None,
            "requested_until": None,
            "interval_seconds": 2.0,
            "preview_width": 960,
            "sequence": 0,
            "latest_at": None,
            "resolution": None,
            "sync_delta_ms": None,
            "quality": None,
            "assets": {"rgb": None, "nir": None},
        }

    active = preview.requested_until > now
    has_current_frame = (
        preview.latest_session_id == preview.session_id
        and preview.latest_at is not None
        and preview.rgb_key is not None
        and preview.nir_key is not None
    )
    freshness_limit = max(15.0, preview.interval_seconds * 6.0)
    fresh = bool(
        active
        and has_current_frame
        and preview.latest_at
        and (now - preview.latest_at).total_seconds() <= freshness_limit
    )
    state = "streaming" if fresh else "waiting" if active else "stopped"
    return {
        "device_id": device.id,
        "device_name": device.name,
        "site_name": device.site_name,
        "active": active,
        "state": state,
        "session_id": preview.session_id,
        "requested_until": preview.requested_until.isoformat() + "Z",
        "interval_seconds": round(preview.interval_seconds, 2),
        "preview_width": preview.preview_width,
        "sequence": preview.sequence if has_current_frame else 0,
        "latest_at": preview.latest_at.isoformat() + "Z"
        if has_current_frame and preview.latest_at
        else None,
        "resolution": {
            "width": preview.width,
            "height": preview.height,
        }
        if has_current_frame
        else None,
        "sync_delta_ms": round(preview.sync_delta_ms, 2)
        if has_current_frame and preview.sync_delta_ms is not None
        else None,
        "quality": {
            "rgb_blur_score": round(preview.rgb_blur_score, 2),
            "nir_blur_score": round(preview.nir_blur_score, 2),
            "rgb_mean": round(preview.rgb_mean, 4),
            "nir_mean": round(preview.nir_mean, 4),
            "rgb_saturated_fraction": round(
                preview.rgb_saturated_fraction,
                5,
            ),
            "nir_saturated_fraction": round(
                preview.nir_saturated_fraction,
                5,
            ),
        }
        if has_current_frame
        and all(
            value is not None
            for value in (
                preview.rgb_blur_score,
                preview.nir_blur_score,
                preview.rgb_mean,
                preview.nir_mean,
                preview.rgb_saturated_fraction,
                preview.nir_saturated_fraction,
            )
        )
        else None,
        "assets": {
            "rgb": media_url(preview.rgb_key) if has_current_frame else None,
            "nir": media_url(preview.nir_key) if has_current_frame else None,
        },
    }


def create_app(
    settings: Settings | None = None,
    webcam_manager: WebcamManager | Any | None = None,
) -> FastAPI:
    app_settings = settings or Settings.from_env()
    app_settings.data_dir.mkdir(parents=True, exist_ok=True)
    database = Database(app_settings.database_url)
    storage = build_storage(app_settings)
    webcam = webcam_manager or WebcamManager(
        enabled=app_settings.webcam_enabled,
        camera_index=app_settings.webcam_index,
        camera_name=app_settings.webcam_name,
        width=app_settings.webcam_width,
        height=app_settings.webcam_height,
        fps=app_settings.webcam_fps,
        zoom=app_settings.webcam_zoom,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database.create_all()
        if app_settings.seed_demo:
            with database.session_factory() as db:
                seed_demo_data(db, storage)
        try:
            yield
        finally:
            webcam.stop()

    app = FastAPI(
        title=f"{app_settings.app_name} API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = app_settings
    app.state.database = database
    app.state.storage = storage
    app.state.webcam = webcam

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

    @app.get("/api/webcam/status")
    def webcam_status() -> dict[str, Any]:
        return webcam.status()

    @app.post("/api/webcam/start")
    def start_webcam() -> dict[str, Any]:
        try:
            return webcam.start()
        except WebcamError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/api/webcam/stop")
    def stop_webcam() -> dict[str, Any]:
        webcam.stop()
        return webcam.status()

    @app.put("/api/webcam/config")
    def configure_webcam(payload: WebcamConfigUpdate) -> dict[str, Any]:
        try:
            return webcam.configure(**payload.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except WebcamError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/webcam/stream.mjpg")
    def stream_webcam() -> StreamingResponse:
        try:
            webcam.start()
        except WebcamError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return StreamingResponse(
            webcam.mjpeg_stream(maximum_fps=10),
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @app.post("/api/webcam/capture", status_code=201)
    def capture_webcam_snapshot(
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        try:
            image_data = webcam.capture_jpeg()
        except WebcamError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        try:
            metrics = analyze_image(image_data)
        except ImageValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        failures = webcam_quality_failures(metrics)
        if failures:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "WEBCAM_QUALITY_REJECTED",
                    "message": "; ".join(failures),
                },
            )

        status = webcam.status()
        configured = status["configured"]
        active = status["active"]
        captured_at = utcnow()
        snapshot_id = str(uuid.uuid4())
        date_key = captured_at.date().isoformat()
        prefix = f"webcam/{date_key}/{snapshot_id}"
        image_key = f"{prefix}/rgb.jpg"
        thumb_key = f"{prefix}/thumb.jpg"
        written: list[str] = []

        try:
            storage.put_bytes(image_key, image_data, "image/jpeg")
            written.append(image_key)
            storage.put_bytes(
                thumb_key,
                make_thumbnail(image_data, width=520),
                "image/jpeg",
            )
            written.append(thumb_key)
            snapshot = WebcamSnapshot(
                id=snapshot_id,
                captured_at=captured_at,
                date_key=date_key,
                image_key=image_key,
                thumb_key=thumb_key,
                width=metrics.width,
                height=metrics.height,
                fps=float(active["fps"]),
                zoom=float(configured["zoom"]),
                blur_score=metrics.blur_score,
                mean_normalized=metrics.mean_normalized,
                dark_fraction=metrics.dark_fraction,
                saturated_fraction=metrics.saturated_fraction,
                camera_name=str(status["camera_name"]),
            )
            db.add(snapshot)
            db.commit()
            db.refresh(snapshot)
        except Exception:
            db.rollback()
            for key in written:
                storage.delete(key)
            raise
        return serialize_webcam_snapshot(snapshot)

    @app.get("/api/webcam/snapshots")
    def list_webcam_snapshots(
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 50,
        db: Session = Depends(get_db),
    ) -> list[dict[str, Any]]:
        query = select(WebcamSnapshot)
        if date_from:
            query = query.where(WebcamSnapshot.date_key >= date_from.isoformat())
        if date_to:
            query = query.where(WebcamSnapshot.date_key <= date_to.isoformat())
        query = query.order_by(WebcamSnapshot.captured_at.desc()).limit(
            min(max(limit, 1), 250)
        )
        return [
            serialize_webcam_snapshot(snapshot)
            for snapshot in db.scalars(query)
        ]

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

    @app.post("/api/devices/{device_id}/preview/start")
    def start_device_preview(
        device_id: str,
        payload: DevicePreviewStart,
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        device = db.get(Device, device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        now = utcnow()
        preview = db.get(DevicePreview, device_id)
        can_extend = bool(
            preview
            and preview.requested_until > now
            and preview.preview_width == payload.preview_width
        )
        if preview is None:
            preview = DevicePreview(
                device_id=device_id,
                session_id=str(uuid.uuid4()),
                requested_until=now,
            )
            db.add(preview)
        elif not can_extend:
            preview.session_id = str(uuid.uuid4())
            preview.sequence = 0
            preview.latest_session_id = None
            preview.latest_at = None

        preview.requested_until = now + timedelta(seconds=payload.session_seconds)
        preview.interval_seconds = payload.interval_seconds
        preview.preview_width = payload.preview_width
        preview.updated_at = now
        db.commit()
        db.refresh(preview)
        return serialize_device_preview(preview, device)

    @app.post("/api/devices/{device_id}/preview/stop")
    def stop_device_preview(
        device_id: str,
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        device = db.get(Device, device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        preview = db.get(DevicePreview, device_id)
        if preview:
            preview.requested_until = utcnow()
            preview.updated_at = utcnow()
            db.commit()
            db.refresh(preview)
        return serialize_device_preview(preview, device)

    @app.get("/api/devices/{device_id}/preview")
    def get_device_preview(
        device_id: str,
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        device = db.get(Device, device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        return serialize_device_preview(db.get(DevicePreview, device_id), device)

    @app.get("/api/devices/{device_id}/preview/request")
    def get_device_preview_request(
        device_id: str,
        x_device_key: str | None = Header(default=None),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        verify_device_key(app_settings, x_device_key)
        if not db.get(Device, device_id):
            raise HTTPException(status_code=404, detail="Device not found")
        preview = db.get(DevicePreview, device_id)
        if preview is None or preview.requested_until <= utcnow():
            return {"active": False}
        return {
            "active": True,
            "session_id": preview.session_id,
            "interval_seconds": preview.interval_seconds,
            "preview_width": preview.preview_width,
            "requested_until": preview.requested_until.isoformat() + "Z",
        }

    @app.post("/api/devices/{device_id}/preview/frame")
    async def upload_device_preview_frame(
        device_id: str,
        session_id: str = Form(...),
        captured_at: str | None = Form(default=None),
        sync_delta_ms: float | None = Form(default=None),
        rgb: UploadFile = File(...),
        nir: UploadFile = File(...),
        x_device_key: str | None = Header(default=None),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        verify_device_key(app_settings, x_device_key)
        device = db.get(Device, device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        preview = db.get(DevicePreview, device_id)
        if (
            preview is None
            or preview.requested_until <= utcnow()
            or preview.session_id != session_id
        ):
            raise HTTPException(
                status_code=409,
                detail="Preview session is no longer active",
            )

        rgb_data = await read_upload(rgb, min(app_settings.max_upload_mb, 12))
        nir_data = await read_upload(nir, min(app_settings.max_upload_mb, 12))
        try:
            rgb_metrics = analyze_image(rgb_data)
            nir_metrics = analyze_image(nir_data)
        except ImageValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if (rgb_metrics.width, rgb_metrics.height) != (
            nir_metrics.width,
            nir_metrics.height,
        ):
            raise HTTPException(
                status_code=422,
                detail="RGB and NIR preview frames must have identical dimensions",
            )

        keys = {
            "rgb": f"previews/{device_id}/rgb.jpg",
            "nir": f"previews/{device_id}/nir.jpg",
        }
        storage.put_bytes(keys["rgb"], rgb_data, rgb.content_type or "image/jpeg")
        storage.put_bytes(keys["nir"], nir_data, nir.content_type or "image/jpeg")

        preview.sequence += 1
        preview.latest_session_id = session_id
        preview.latest_at = parse_datetime(captured_at)
        preview.rgb_key = keys["rgb"]
        preview.nir_key = keys["nir"]
        preview.width = rgb_metrics.width
        preview.height = rgb_metrics.height
        preview.sync_delta_ms = sync_delta_ms
        preview.rgb_blur_score = rgb_metrics.blur_score
        preview.nir_blur_score = nir_metrics.blur_score
        preview.rgb_mean = rgb_metrics.mean_normalized
        preview.nir_mean = nir_metrics.mean_normalized
        preview.rgb_saturated_fraction = rgb_metrics.saturated_fraction
        preview.nir_saturated_fraction = nir_metrics.saturated_fraction
        preview.updated_at = utcnow()
        device.last_seen_at = utcnow()
        device.status = "online"
        device.updated_at = utcnow()
        db.commit()
        db.refresh(preview)
        return serialize_device_preview(preview, device)

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

    @app.post("/api/devices/{device_id}/commands", status_code=201)
    def create_device_command(
        device_id: str,
        payload: DeviceCommandCreate,
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        if not db.get(Device, device_id):
            raise HTTPException(status_code=404, detail="Device not found")
        command = DeviceCommand(
            id=str(uuid.uuid4()),
            device_id=device_id,
            command_type=payload.type,
            status="pending",
            payload_json=json.dumps(payload.payload, separators=(",", ":")),
        )
        db.add(command)
        db.commit()
        db.refresh(command)
        return serialize_command(command)

    @app.get("/api/devices/{device_id}/commands")
    def list_device_commands(
        device_id: str,
        limit: int = 20,
        db: Session = Depends(get_db),
    ) -> list[dict[str, Any]]:
        if not db.get(Device, device_id):
            raise HTTPException(status_code=404, detail="Device not found")
        commands = db.scalars(
            select(DeviceCommand)
            .where(DeviceCommand.device_id == device_id)
            .order_by(DeviceCommand.created_at.desc())
            .limit(min(max(limit, 1), 100))
        )
        return [serialize_command(command) for command in commands]

    @app.get("/api/devices/{device_id}/commands/{command_id}")
    def get_device_command(
        device_id: str,
        command_id: str,
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        command = db.get(DeviceCommand, command_id)
        if command is None or command.device_id != device_id:
            raise HTTPException(status_code=404, detail="Command not found")
        return serialize_command(command)

    @app.post("/api/devices/{device_id}/commands/claim")
    def claim_device_command(
        device_id: str,
        x_device_key: str | None = Header(default=None),
        db: Session = Depends(get_db),
    ) -> dict[str, Any] | None:
        verify_device_key(app_settings, x_device_key)
        if not db.get(Device, device_id):
            raise HTTPException(status_code=404, detail="Device not found")
        stale_before = utcnow() - timedelta(minutes=5)
        command = db.scalar(
            select(DeviceCommand)
            .where(
                DeviceCommand.device_id == device_id,
                or_(
                    DeviceCommand.status == "pending",
                    and_(
                        DeviceCommand.status == "running",
                        DeviceCommand.claimed_at < stale_before,
                    ),
                ),
            )
            .order_by(DeviceCommand.created_at)
            .limit(1)
        )
        if command is None:
            return None
        command.status = "running"
        command.claimed_at = utcnow()
        db.commit()
        db.refresh(command)
        return serialize_command(command)

    @app.post("/api/devices/{device_id}/commands/{command_id}/complete")
    def complete_device_command(
        device_id: str,
        command_id: str,
        payload: DeviceCommandComplete,
        x_device_key: str | None = Header(default=None),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        verify_device_key(app_settings, x_device_key)
        command = db.get(DeviceCommand, command_id)
        if command is None or command.device_id != device_id:
            raise HTTPException(status_code=404, detail="Command not found")
        if command.status not in {"pending", "running"}:
            return serialize_command(command)
        command.status = payload.status
        command.completed_at = utcnow()
        command.result_json = json.dumps(
            {
                "capture_id": payload.capture_id,
                "message": payload.message,
            },
            separators=(",", ":"),
        )
        db.commit()
        db.refresh(command)
        return serialize_command(command)

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
        capture_id: str | None = Form(default=None),
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
        if capture_id and len(capture_id) > 80:
            raise HTTPException(status_code=422, detail="capture_id is too long")
        if capture_id:
            existing = db.scalar(
                select(Capture)
                .options(selectinload(Capture.device))
                .where(Capture.id == capture_id)
            )
            if existing:
                if existing.device_id != device_id:
                    raise HTTPException(
                        status_code=409,
                        detail="capture_id belongs to another device",
                    )
                return JSONResponse(
                    status_code=200,
                    content=serialize_capture(existing, include_metadata=True),
                )

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
        capture_id = capture_id or str(uuid.uuid4())
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
