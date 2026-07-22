from __future__ import annotations

import io
import json
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.models import Device
from app.profiles import default_capture_profile


@pytest.fixture()
def client(tmp_path: Path):
    settings = Settings(
        database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        data_dir=tmp_path,
        static_dir=Path(__file__).resolve().parents[1] / "app" / "static",
        storage_backend="local",
        seed_demo=False,
        max_upload_mb=10,
    )
    app = create_app(settings)
    with TestClient(app) as test_client:
        profile = default_capture_profile()
        with app.state.database.session_factory() as db:
            db.add(
                Device(
                    id="test-node",
                    name="Test Node",
                    site_name="Test Plot",
                    status="online",
                    firmware_version="test",
                    calibration_id="CAL-TEST-1",
                    capture_interval_minutes=15,
                    profile_json=json.dumps(profile),
                )
            )
            db.commit()
        yield test_client, app


def encode_jpeg(image: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 92])
    assert ok
    return encoded.tobytes()


def sharp_pair(width: int = 480, height: int = 270) -> tuple[bytes, bytes]:
    y, x = np.mgrid[0:height, 0:width]
    checker = ((x // 12 + y // 12) % 2).astype(np.uint8)
    rgb = np.zeros((height, width, 3), dtype=np.uint8)
    rgb[:, :, 0] = 45 + checker * 25
    rgb[:, :, 1] = 100 + checker * 60
    rgb[:, :, 2] = 55 + checker * 30
    nir_value = 175 + checker * 45
    nir = cv2.merge([nir_value, nir_value, nir_value])
    return encode_jpeg(rgb), encode_jpeg(nir)


def upload(
    client: TestClient,
    rgb: bytes,
    nir: bytes,
    *,
    source: str = "manual",
    metadata: dict | None = None,
) -> object:
    return client.post(
        "/api/captures",
        data={
            "device_id": "test-node",
            "captured_at": "2026-07-22T10:00:00Z",
            "source": source,
            "sync_delta_ms": "420",
            "metadata": json.dumps(metadata or {}),
        },
        files={
            "rgb": ("rgb.jpg", io.BytesIO(rgb), "image/jpeg"),
            "nir": ("nir.jpg", io.BytesIO(nir), "image/jpeg"),
        },
    )


def test_health_dashboard_and_profile(client):
    http, _ = client
    assert http.get("/api/health").status_code == 200
    dashboard = http.get("/api/dashboard").json()
    assert dashboard["summary"]["total_devices"] == 1
    profile = http.get("/api/devices/test-node/capture-profile")
    assert profile.status_code == 200
    assert profile.json()["profile"]["cameras"]["rgb"]["awb_enabled"] is False


def test_manual_upload_calculates_ndvi_and_serves_assets(client):
    http, _ = client
    rgb, nir = sharp_pair()
    response = upload(http, rgb, nir)
    assert response.status_code == 201, response.text
    capture = response.json()
    assert capture["ndvi"]["mean"] > 0.2
    assert capture["resolution"] == {"width": 480, "height": 270}
    assert capture["quality_state"] == "warning"
    assert "camera_controls_missing" in capture["quality_flags"]
    assert http.get(capture["assets"]["ndvi"]).status_code == 200
    assert http.get(capture["assets"]["ndvi_data"]).status_code == 200


def test_manual_upload_resamples_matching_aspect_ratio(client):
    http, _ = client
    rgb, _ = sharp_pair(width=480, height=270)
    _, nir = sharp_pair(width=240, height=135)

    response = upload(http, rgb, nir)

    assert response.status_code == 201, response.text
    capture = response.json()
    assert capture["resolution"] == {"width": 480, "height": 270}
    assert "nir_resampled_to_rgb" in capture["quality_flags"]
    ndvi_image = cv2.imdecode(
        np.frombuffer(http.get(capture["assets"]["ndvi"]).content, dtype=np.uint8),
        cv2.IMREAD_COLOR,
    )
    assert ndvi_image.shape[:2] == (270, 480)


def test_manual_upload_rejects_different_aspect_ratios(client):
    http, _ = client
    rgb, _ = sharp_pair(width=480, height=270)
    _, nir = sharp_pair(width=320, height=240)

    response = upload(http, rgb, nir)

    assert response.status_code == 422
    message = response.json()["detail"]["message"]
    assert "RGB is 480x270; NIR is 320x240" in message
    assert "aspect ratios differ" in message


def test_manual_upload_flags_and_masks_saturated_pixels(client):
    http, _ = client
    rgb, nir = sharp_pair()
    nir_image = cv2.imdecode(np.frombuffer(nir, dtype=np.uint8), cv2.IMREAD_COLOR)
    nir_image[:60, :, :] = 255

    response = upload(http, rgb, encode_jpeg(nir_image))

    assert response.status_code == 201, response.text
    capture = response.json()
    assert capture["quality_state"] == "warning"
    assert "nir_saturation_high" in capture["quality_flags"]
    matrix_response = http.get(capture["assets"]["ndvi_data"])
    with np.load(io.BytesIO(matrix_response.content)) as matrix:
        assert float(np.mean(~matrix["valid"])) > 0.20


def test_blurred_pair_is_rejected(client):
    http, _ = client
    flat = np.full((270, 480, 3), 110, dtype=np.uint8)
    response = upload(http, encode_jpeg(flat), encode_jpeg(flat))
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "IMAGE_QUALITY_REJECTED"
    assert "blur score" in response.json()["detail"]["message"]


def test_device_upload_rejects_control_drift(client):
    http, app = client
    profile = default_capture_profile()
    profile["resolution"] = {"width": 480, "height": 270}
    for camera in profile["cameras"].values():
        camera["scaler_crop"] = [0, 0, 480, 270]
    with app.state.database.session_factory() as db:
        device = db.get(Device, "test-node")
        device.profile_json = json.dumps(profile)
        db.commit()

    rgb, nir = sharp_pair()
    metadata = {
        "rgb_controls": {
            "ae_enabled": False,
            "awb_enabled": True,
            "scaler_crop": [0, 0, 480, 270],
            "lens_position": 3.2,
            "colour_gains": [1.75, 1.55],
            "profile_id": "overcast",
            "exposure_us": 4000,
            "analogue_gain": 1.0,
        },
        "nir_controls": {
            "ae_enabled": False,
            "awb_enabled": False,
            "scaler_crop": [0, 0, 480, 270],
            "lens_position": 3.6,
            "colour_gains": [1.0, 1.0],
            "profile_id": "overcast",
            "exposure_us": 8000,
            "analogue_gain": 1.5,
        },
    }
    response = upload(http, rgb, nir, source="device", metadata=metadata)
    assert response.status_code == 422
    assert "automatic white balance must be disabled" in response.json()["detail"]["message"]


def test_heartbeat_updates_wifi_state(client):
    http, _ = client
    response = http.post(
        "/api/devices/test-node/heartbeat",
        json={
            "status": "online",
            "wifi_ssid": "FieldLab",
            "wifi_rssi_dbm": -62,
            "queue_depth": 4,
            "storage_used_percent": 22.5,
            "battery_percent": 73,
        },
    )
    assert response.status_code == 200
    assert response.json()["wifi_ssid"] == "FieldLab"
    assert response.json()["queue_depth"] == 4
