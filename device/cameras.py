from __future__ import annotations

import io
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Protocol

import cv2
import numpy as np

from .models import CameraFrame, CapturedPair
from .quality import encode_jpeg


class CameraPair(Protocol):
    def capture(
        self,
        profile: dict[str, Any],
        profile_id: str,
    ) -> CapturedPair:
        ...

    def close(self) -> None:
        ...


def resize_preview_jpeg(data: bytes, maximum_width: int) -> bytes:
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Preview frame could not be decoded")
    height, width = image.shape[:2]
    if width <= maximum_width:
        return encode_jpeg(image, quality=84)
    output_height = max(1, round(height * maximum_width / width))
    resized = cv2.resize(
        image,
        (maximum_width, output_height),
        interpolation=cv2.INTER_AREA,
    )
    return encode_jpeg(resized, quality=84)


def select_exposure_profile(profile: dict[str, Any], illuminance_lux: float | None) -> str:
    profiles = profile["cameras"]["rgb"]["exposure_profiles"]
    if illuminance_lux is None and "overcast" in profiles:
        return "overcast"
    lux = float(illuminance_lux or 0.0)
    ordered = sorted(
        profiles.items(),
        key=lambda item: float(item[1]["minimum_lux"]),
    )
    selected = ordered[0][0]
    for name, settings in ordered:
        if lux >= float(settings["minimum_lux"]):
            selected = name
    return selected


def control_metadata(
    camera_profile: dict[str, Any],
    exposure_profile: dict[str, Any],
    profile_id: str,
    actual: dict[str, Any] | None = None,
) -> dict[str, Any]:
    actual = actual or {}
    gains = actual.get("ColourGains") or camera_profile["colour_gains"]
    crop = actual.get("ScalerCrop") or camera_profile["scaler_crop"]
    if all(hasattr(crop, field) for field in ("x", "y", "width", "height")):
        crop_values = [crop.x, crop.y, crop.width, crop.height]
    else:
        crop_values = list(crop)
    lens_position = actual.get("LensPosition")
    exposure_us = actual.get("ExposureTime")
    analogue_gain = actual.get("AnalogueGain")
    return {
        "ae_enabled": False,
        "awb_enabled": False,
        "scaler_crop": [int(value) for value in crop_values],
        "lens_position": float(
            camera_profile["lens_position"]
            if lens_position is None
            else lens_position
        ),
        "colour_gains": [float(value) for value in gains],
        "profile_id": profile_id,
        "exposure_us": float(
            exposure_profile["exposure_us"]
            if exposure_us is None
            else exposure_us
        ),
        "analogue_gain": float(
            exposure_profile["analogue_gain"]
            if analogue_gain is None
            else analogue_gain
        ),
    }


class SimulatedCameraPair:
    def capture(
        self,
        profile: dict[str, Any],
        profile_id: str,
    ) -> CapturedPair:
        resolution = profile["resolution"]
        width = int(resolution["width"])
        height = int(resolution["height"])
        rgb_data, nir_data = self._generate_pair(width, height)
        now = datetime.now(timezone.utc)
        rgb_timestamp = time.monotonic_ns()
        nir_timestamp = rgb_timestamp + 8_000_000
        rgb_profile = profile["cameras"]["rgb"]
        nir_profile = profile["cameras"]["nir"]
        return CapturedPair(
            rgb=CameraFrame(
                data=rgb_data,
                captured_at=now,
                sensor_timestamp_ns=rgb_timestamp,
                controls=control_metadata(
                    rgb_profile,
                    rgb_profile["exposure_profiles"][profile_id],
                    profile_id,
                ),
            ),
            nir=CameraFrame(
                data=nir_data,
                captured_at=now,
                sensor_timestamp_ns=nir_timestamp,
                controls=control_metadata(
                    nir_profile,
                    nir_profile["exposure_profiles"][profile_id],
                    profile_id,
                ),
            ),
            profile_id=profile_id,
        )

    def close(self) -> None:
        return

    @staticmethod
    def _generate_pair(width: int, height: int) -> tuple[bytes, bytes]:
        base_width = min(width, 960)
        base_height = max(1, round(height * base_width / width))
        y, x = np.mgrid[0:base_height, 0:base_width]
        tile = max(5, base_width // 80)
        checker = ((x // tile + y // tile) % 2).astype(np.uint8)
        wave = ((np.sin(x / 21.0) + 1.0) * 16.0).astype(np.uint8)

        rgb = np.zeros((base_height, base_width, 3), dtype=np.uint8)
        rgb[:, :, 0] = 42 + checker * 22
        rgb[:, :, 1] = 105 + checker * 58 + wave
        rgb[:, :, 2] = 54 + checker * 28
        nir_value = np.clip(168 + checker * 48 + wave, 0, 245).astype(np.uint8)
        nir = cv2.merge([nir_value, nir_value, nir_value])

        if (base_width, base_height) != (width, height):
            rgb = cv2.resize(rgb, (width, height), interpolation=cv2.INTER_NEAREST)
            nir = cv2.resize(nir, (width, height), interpolation=cv2.INTER_NEAREST)
        return encode_jpeg(rgb), encode_jpeg(nir)


class Picamera2CameraPair:
    def __init__(self, rgb_index: int = 0, nir_index: int = 1) -> None:
        self.rgb_index = rgb_index
        self.nir_index = nir_index
        self.rgb_camera: Any | None = None
        self.nir_camera: Any | None = None
        self.configured_size: tuple[int, int] | None = None
        self.running = False

    def _ensure_configured(self, profile: dict[str, Any]) -> None:
        resolution = profile["resolution"]
        size = (int(resolution["width"]), int(resolution["height"]))
        if self.configured_size == size:
            return
        self.close()
        try:
            from picamera2 import Picamera2
        except ImportError as exc:
            raise RuntimeError(
                "Picamera2 is unavailable. Install it through Raspberry Pi OS "
                "or set simulate=true."
            ) from exc

        self.rgb_camera = Picamera2(self.rgb_index)
        self.nir_camera = Picamera2(self.nir_index)
        for camera in (self.rgb_camera, self.nir_camera):
            config = camera.create_still_configuration(
                main={"size": size, "format": "RGB888"},
                buffer_count=3,
            )
            camera.configure(config)
        self.configured_size = size

    @staticmethod
    def _picamera_controls(
        camera_profile: dict[str, Any],
        exposure_profile: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            from libcamera import controls
        except ImportError as exc:
            raise RuntimeError("libcamera Python controls are unavailable") from exc
        return {
            "AeEnable": False,
            "AwbEnable": False,
            "AfMode": controls.AfModeEnum.Manual,
            "LensPosition": float(camera_profile["lens_position"]),
            "ColourGains": tuple(float(value) for value in camera_profile["colour_gains"]),
            "ScalerCrop": tuple(int(value) for value in camera_profile["scaler_crop"]),
            "ExposureTime": int(exposure_profile["exposure_us"]),
            "AnalogueGain": float(exposure_profile["analogue_gain"]),
        }

    def capture(
        self,
        profile: dict[str, Any],
        profile_id: str,
    ) -> CapturedPair:
        self._ensure_configured(profile)
        assert self.rgb_camera is not None
        assert self.nir_camera is not None
        rgb_profile = profile["cameras"]["rgb"]
        nir_profile = profile["cameras"]["nir"]
        rgb_exposure = rgb_profile["exposure_profiles"][profile_id]
        nir_exposure = nir_profile["exposure_profiles"][profile_id]
        rgb_controls = self._picamera_controls(rgb_profile, rgb_exposure)
        nir_controls = self._picamera_controls(nir_profile, nir_exposure)

        sync_enabled = False
        try:
            from libcamera import controls

            sync_enum = controls.rpi.SyncModeEnum
            rgb_controls["SyncMode"] = sync_enum.Server
            nir_controls["SyncMode"] = sync_enum.Client
            sync_enabled = True
        except (AttributeError, ImportError):
            pass

        self.rgb_camera.set_controls(rgb_controls)
        self.nir_camera.set_controls(nir_controls)
        if not self.running:
            self.nir_camera.start()
            self.rgb_camera.start()
            self.running = True
            time.sleep(1.0 if sync_enabled else 0.5)
        else:
            time.sleep(0.2)

        rgb_capture = getattr(
            self.rgb_camera,
            "capture_sync_request",
            self.rgb_camera.capture_request,
        )
        nir_capture = getattr(
            self.nir_camera,
            "capture_sync_request",
            self.nir_camera.capture_request,
        )
        with ThreadPoolExecutor(max_workers=2) as pool:
            rgb_future = pool.submit(rgb_capture)
            nir_future = pool.submit(nir_capture)
            rgb_request = rgb_future.result(timeout=30)
            nir_request = nir_future.result(timeout=30)

        try:
            rgb_metadata = rgb_request.get_metadata()
            nir_metadata = nir_request.get_metadata()
            rgb_data = self._request_jpeg(rgb_request)
            nir_data = self._request_jpeg(nir_request)
        finally:
            rgb_request.release()
            nir_request.release()

        now = datetime.now(timezone.utc)
        rgb_timestamp = int(rgb_metadata.get("SensorTimestamp", time.monotonic_ns()))
        nir_timestamp = int(nir_metadata.get("SensorTimestamp", time.monotonic_ns()))
        return CapturedPair(
            rgb=CameraFrame(
                data=rgb_data,
                captured_at=now,
                sensor_timestamp_ns=rgb_timestamp,
                controls=control_metadata(
                    rgb_profile,
                    rgb_exposure,
                    profile_id,
                    rgb_metadata,
                ),
            ),
            nir=CameraFrame(
                data=nir_data,
                captured_at=now,
                sensor_timestamp_ns=nir_timestamp,
                controls=control_metadata(
                    nir_profile,
                    nir_exposure,
                    profile_id,
                    nir_metadata,
                ),
            ),
            profile_id=profile_id,
        )

    @staticmethod
    def _request_jpeg(request: Any) -> bytes:
        image = request.make_image("main")
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=92)
        return output.getvalue()

    def close(self) -> None:
        for camera in (self.rgb_camera, self.nir_camera):
            if camera is None:
                continue
            try:
                camera.stop()
            except RuntimeError:
                pass
            camera.close()
        self.rgb_camera = None
        self.nir_camera = None
        self.configured_size = None
        self.running = False
