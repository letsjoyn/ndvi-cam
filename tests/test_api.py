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
from device.agent import DeviceAgent
from device.api import RetryableApiError
from device.cameras import SimulatedCameraPair
from device.config import AgentConfig
from device.models import QueueItem
from device.registration import PairRegistrar
from device.sensors import SimulatedSensorSuite


class FakeWebcamManager:
    def __init__(self) -> None:
        self.enabled = True
        self.running = False
        self.camera_name = "Test RGB Camera"
        self.configured = {
            "width": 1280,
            "height": 720,
            "fps": 30,
            "zoom": 1.0,
        }
        self.image_data: bytes | None = None

    def start(self) -> dict:
        self.running = True
        return self.status()

    def stop(self) -> None:
        self.running = False

    def configure(self, *, width: int, height: int, fps: int, zoom: float) -> dict:
        if (width, height) not in {
            (640, 480),
            (1280, 720),
            (1920, 1080),
        }:
            raise ValueError("Unsupported webcam resolution")
        self.configured = {
            "width": width,
            "height": height,
            "fps": fps,
            "zoom": zoom,
        }
        return self.status()

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "running": self.running,
            "camera_index": 0,
            "camera_name": self.camera_name,
            "configured": dict(self.configured),
            "active": {
                "width": self.configured["width"],
                "height": self.configured["height"],
                "fps": float(self.configured["fps"]),
            },
            "frame": {
                "captured_at": "2026-07-22T10:00:00+00:00",
                "age_ms": 5.0,
                "brightness": 0.45,
                "sharpness": 240.0,
                "dark_fraction": 0.01,
                "saturated_fraction": 0.01,
            }
            if self.running
            else None,
            "error": None,
        }

    def capture_jpeg(self, timeout: float = 5.0) -> bytes:
        del timeout
        self.running = True
        if self.image_data is not None:
            return self.image_data
        rgb, _ = sharp_pair()
        return rgb

    def mjpeg_stream(self, maximum_fps: int = 10):
        del maximum_fps
        self.running = True
        yield (
            b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
            + self.capture_jpeg()
            + b"\r\n"
        )


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
    app = create_app(settings, webcam_manager=FakeWebcamManager())
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


class BackendHarness:
    def __init__(
        self,
        http: TestClient,
        *,
        device_id: str = "test-node",
        fail_upload: bool = False,
    ) -> None:
        self.http = http
        self.device_id = device_id
        self.fail_upload = fail_upload

    def get_profile(self) -> dict:
        response = self.http.get(
            f"/api/devices/{self.device_id}/capture-profile"
        )
        assert response.status_code == 200
        return response.json()

    def upload_capture(self, item: QueueItem) -> dict:
        if self.fail_upload:
            raise RetryableApiError("network offline")
        with item.rgb_path.open("rb") as rgb, item.nir_path.open("rb") as nir:
            response = self.http.post(
                "/api/captures",
                data={
                    "capture_id": item.capture_id,
                    "device_id": self.device_id,
                    "captured_at": item.manifest["captured_at"],
                    "source": "device",
                    "sync_delta_ms": str(item.manifest["sync_delta_ms"]),
                    "metadata": json.dumps(item.manifest["metadata"]),
                },
                files={
                    "rgb": ("rgb.jpg", rgb, "image/jpeg"),
                    "nir": ("nir.jpg", nir, "image/jpeg"),
                },
            )
        assert response.status_code in {200, 201}, response.text
        return response.json()

    def heartbeat(self, payload: dict) -> dict:
        response = self.http.post(
            f"/api/devices/{self.device_id}/heartbeat",
            json=payload,
        )
        assert response.status_code == 200
        return response.json()

    def claim_command(self) -> dict | None:
        response = self.http.post(
            f"/api/devices/{self.device_id}/commands/claim"
        )
        assert response.status_code == 200
        return response.json()

    def complete_command(
        self,
        command_id: str,
        *,
        status: str,
        capture_id: str | None,
        message: str | None,
    ) -> dict:
        response = self.http.post(
            f"/api/devices/{self.device_id}/commands/{command_id}/complete",
            json={
                "status": status,
                "capture_id": capture_id,
                "message": message,
            },
        )
        assert response.status_code == 200
        return response.json()

    def get_preview_request(self) -> dict:
        response = self.http.get(
            f"/api/devices/{self.device_id}/preview/request"
        )
        assert response.status_code == 200
        return response.json()

    def upload_preview(
        self,
        *,
        session_id: str,
        captured_at: str,
        sync_delta_ms: float,
        rgb_data: bytes,
        nir_data: bytes,
    ) -> dict:
        response = self.http.post(
            f"/api/devices/{self.device_id}/preview/frame",
            data={
                "session_id": session_id,
                "captured_at": captured_at,
                "sync_delta_ms": str(sync_delta_ms),
            },
            files={
                "rgb": ("rgb-preview.jpg", io.BytesIO(rgb_data), "image/jpeg"),
                "nir": ("nir-preview.jpg", io.BytesIO(nir_data), "image/jpeg"),
            },
        )
        assert response.status_code == 200, response.text
        return response.json()

    def close(self) -> None:
        return


def agent_config(tmp_path: Path) -> AgentConfig:
    return AgentConfig(
        device_id="test-node",
        api_base_url="http://testserver",
        device_key="",
        queue_path=tmp_path / "queue",
        registration_file=None,
        simulate=True,
        rgb_camera_index=0,
        nir_camera_index=1,
        poll_seconds=1,
        profile_refresh_seconds=60,
        heartbeat_seconds=60,
        retry_base_seconds=1,
        retry_max_seconds=10,
        capture_retry_count=1,
        capture_on_start=False,
        align_to_interval=True,
        simulated_illuminance_lux=7500,
        verify_tls=False,
        firmware_version="test-agent",
    )


def configure_small_device_profile(http: TestClient, app) -> None:
    profile = default_capture_profile()
    profile["resolution"] = {"width": 480, "height": 270}
    for camera in profile["cameras"].values():
        camera["scaler_crop"] = [0, 0, 480, 270]
    with app.state.database.session_factory() as db:
        device = db.get(Device, "test-node")
        device.profile_json = json.dumps(profile)
        db.commit()


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


def test_interval_update_and_capture_command_lifecycle(client):
    http, _ = client
    current = http.get("/api/devices/test-node/capture-profile").json()
    update = http.put(
        "/api/devices/test-node/capture-profile",
        json={
            "calibration_id": current["calibration_id"],
            "capture_interval_minutes": 20,
            "profile": current["profile"],
        },
    )
    assert update.status_code == 200
    assert update.json()["capture_interval_minutes"] == 20

    created = http.post(
        "/api/devices/test-node/commands",
        json={"type": "capture_now", "payload": {"requested_by": "test"}},
    )
    assert created.status_code == 201
    command_id = created.json()["id"]
    assert created.json()["status"] == "pending"

    claimed = http.post("/api/devices/test-node/commands/claim")
    assert claimed.status_code == 200
    assert claimed.json()["id"] == command_id
    assert claimed.json()["status"] == "running"
    assert http.post("/api/devices/test-node/commands/claim").json() is None

    completed = http.post(
        f"/api/devices/test-node/commands/{command_id}/complete",
        json={
            "status": "completed",
            "capture_id": "capture-test-1",
            "message": "Uploaded",
        },
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["result"]["capture_id"] == "capture-test-1"


def test_webcam_control_capture_and_snapshot_archive(client):
    http, _ = client

    initial = http.get("/api/webcam/status")
    assert initial.status_code == 200
    assert initial.json()["running"] is False

    started = http.post("/api/webcam/start")
    assert started.status_code == 200
    assert started.json()["running"] is True
    assert started.json()["camera_name"] == "Test RGB Camera"

    configured = http.put(
        "/api/webcam/config",
        json={
            "width": 1920,
            "height": 1080,
            "fps": 15,
            "zoom": 1.8,
        },
    )
    assert configured.status_code == 200
    assert configured.json()["configured"] == {
        "width": 1920,
        "height": 1080,
        "fps": 15,
        "zoom": 1.8,
    }

    captured = http.post("/api/webcam/capture")
    assert captured.status_code == 201, captured.text
    snapshot = captured.json()
    assert snapshot["camera_name"] == "Test RGB Camera"
    assert snapshot["zoom"] == 1.8
    assert set(snapshot["assets"]) == {"rgb", "thumb"}
    assert "ndvi" not in snapshot["assets"]
    assert http.get(snapshot["assets"]["rgb"]).status_code == 200
    assert http.get(snapshot["assets"]["thumb"]).status_code == 200

    archive = http.get("/api/webcam/snapshots").json()
    assert len(archive) == 1
    assert archive[0]["id"] == snapshot["id"]

    stopped = http.post("/api/webcam/stop")
    assert stopped.status_code == 200
    assert stopped.json()["running"] is False


def test_webcam_rejects_invalid_mode_and_blurred_snapshot(client):
    http, app = client
    invalid = http.put(
        "/api/webcam/config",
        json={
            "width": 640,
            "height": 720,
            "fps": 30,
            "zoom": 1.0,
        },
    )
    assert invalid.status_code == 422

    flat = np.full((270, 480, 3), 120, dtype=np.uint8)
    app.state.webcam.image_data = encode_jpeg(flat)
    rejected = http.post("/api/webcam/capture")
    assert rejected.status_code == 422
    assert rejected.json()["detail"]["code"] == "WEBCAM_QUALITY_REJECTED"
    assert "too blurry" in rejected.json()["detail"]["message"]
    assert http.get("/api/webcam/snapshots").json() == []


def test_simulated_device_agent_captures_and_uploads(client, tmp_path):
    http, app = client
    configure_small_device_profile(http, app)
    backend = BackendHarness(http)
    agent = DeviceAgent(
        agent_config(tmp_path),
        backend,
        SimulatedCameraPair(),
        SimulatedSensorSuite(7500),
        PairRegistrar("PAIR-TEST", np.eye(3), None),
    )

    local_capture_id = agent.run_once(reason="test")

    captures = http.get("/api/captures?limit=10").json()
    assert len(captures) == 1
    assert captures[0]["id"] == local_capture_id
    assert captures[0]["source"] == "device"
    assert captures[0]["sync_delta_ms"] == 8.0
    assert agent.queue.depth() == 0


def test_simulated_device_agent_keeps_capture_when_offline(client, tmp_path):
    http, app = client
    configure_small_device_profile(http, app)
    backend = BackendHarness(http, fail_upload=True)
    agent = DeviceAgent(
        agent_config(tmp_path),
        backend,
        SimulatedCameraPair(),
        SimulatedSensorSuite(7500),
        PairRegistrar("PAIR-TEST", np.eye(3), None),
    )
    agent.refresh_profile(force=True)

    capture_id = agent.capture(reason="offline-test")
    assert agent.flush_queue() == []

    assert agent.queue.depth() == 1
    queued = agent.queue.ready(now=float("inf"))[0]
    assert queued.capture_id == capture_id
    assert queued.manifest["attempts"] == 1
    assert queued.rgb_path.exists()
    assert queued.nir_path.exists()


def test_simulated_device_agent_consumes_capture_now_command(client, tmp_path):
    http, app = client
    configure_small_device_profile(http, app)
    created = http.post(
        "/api/devices/test-node/commands",
        json={"type": "capture_now", "payload": {}},
    ).json()
    agent = DeviceAgent(
        agent_config(tmp_path),
        BackendHarness(http),
        SimulatedCameraPair(),
        SimulatedSensorSuite(7500),
        PairRegistrar("PAIR-TEST", np.eye(3), None),
    )
    agent.refresh_profile(force=True)

    capture_id = agent.process_next_command()

    command = http.get("/api/devices/test-node/commands").json()[0]
    assert command["id"] == created["id"]
    assert command["status"] == "completed"
    assert command["result"]["capture_id"] == capture_id


def test_simulated_device_agent_uploads_remote_rgb_nir_preview(client, tmp_path):
    http, app = client
    configure_small_device_profile(http, app)
    started = http.post(
        "/api/devices/test-node/preview/start",
        json={
            "interval_seconds": 1,
            "preview_width": 320,
            "session_seconds": 60,
        },
    )
    assert started.status_code == 200
    assert started.json()["state"] == "waiting"

    agent = DeviceAgent(
        agent_config(tmp_path),
        BackendHarness(http),
        SimulatedCameraPair(),
        SimulatedSensorSuite(7500),
        PairRegistrar("PAIR-TEST", np.eye(3), None),
    )
    agent.refresh_profile(force=True)

    preview = agent.process_preview()

    assert preview is not None
    assert preview["state"] == "streaming"
    assert preview["sequence"] == 1
    assert preview["resolution"] == {"width": 320, "height": 180}
    assert preview["sync_delta_ms"] == 8.0
    assert preview["quality"]["rgb_blur_score"] > 0
    assert http.get(preview["assets"]["rgb"]).status_code == 200
    assert http.get(preview["assets"]["nir"]).status_code == 200

    request = http.get("/api/devices/test-node/preview/request").json()
    assert request["active"] is True
    assert request["session_id"] == started.json()["session_id"]

    stopped = http.post("/api/devices/test-node/preview/stop")
    assert stopped.status_code == 200
    assert stopped.json()["state"] == "stopped"
    assert agent.process_preview() is None
