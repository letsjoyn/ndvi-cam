from __future__ import annotations

import json
import logging
import os
import shutil
import socket
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from .api import DeviceBackend, NonRetryableApiError, RetryableApiError
from .cameras import CameraPair, resize_preview_jpeg, select_exposure_profile
from .config import AgentConfig
from .quality import DeviceImageError, validate_pair
from .queue import CaptureQueue
from .registration import PairRegistrar
from .sensors import SensorSuite


LOGGER = logging.getLogger("fieldscope.device")


class DeviceAgent:
    def __init__(
        self,
        config: AgentConfig,
        backend: DeviceBackend,
        cameras: CameraPair,
        sensors: SensorSuite,
        registrar: PairRegistrar,
    ) -> None:
        self.config = config
        self.backend = backend
        self.cameras = cameras
        self.sensors = sensors
        self.registrar = registrar
        self.queue = CaptureQueue(
            config.queue_path,
            retry_base_seconds=config.retry_base_seconds,
            retry_max_seconds=config.retry_max_seconds,
        )
        self.profile_response: dict[str, Any] | None = None
        self.last_profile_refresh = 0.0
        self.profile_cache_path = self.config.queue_path / "profile-cache.json"
        self.preview_session_id: str | None = None
        self.next_preview_at = 0.0

    def refresh_profile(self, *, force: bool = False) -> dict[str, Any]:
        now = time.monotonic()
        if (
            force
            or self.profile_response is None
            or now - self.last_profile_refresh >= self.config.profile_refresh_seconds
        ):
            try:
                self.profile_response = self.backend.get_profile()
                self._write_profile_cache(self.profile_response)
                self.last_profile_refresh = now
            except RetryableApiError:
                if self.profile_response is not None:
                    return self.profile_response
                if self.profile_cache_path.exists():
                    self.profile_response = json.loads(
                        self.profile_cache_path.read_text(encoding="utf-8")
                    )
                    LOGGER.warning("Using cached capture profile")
                    return self.profile_response
                raise
        return self.profile_response

    def capture(
        self,
        *,
        reason: str,
        command_id: str | None = None,
    ) -> str:
        profile_response = self.refresh_profile()
        profile = profile_response["profile"]
        environment = self.sensors.read()
        profile_id = select_exposure_profile(
            profile,
            environment.get("illuminance_lux"),
        )

        last_error: Exception | None = None
        for attempt in range(self.config.capture_retry_count + 1):
            try:
                pair = self.cameras.capture(profile, profile_id)
                aligned_nir, registration = self.registrar.align_nir(
                    pair.rgb.data,
                    pair.nir.data,
                )
                rgb_quality, nir_quality, _ = validate_pair(
                    pair.rgb.data,
                    aligned_nir,
                    profile,
                )
                if pair.sync_delta_ms > float(profile["maximum_sync_delta_ms"]):
                    raise DeviceImageError(
                        f"RGB/NIR capture delta {pair.sync_delta_ms:.1f} ms exceeds "
                        f"{profile['maximum_sync_delta_ms']} ms"
                    )
                capture_id = str(uuid.uuid4())
                metadata = {
                    "calibration_id": profile_response["calibration_id"],
                    "camera_pair_calibration_id": self.registrar.calibration_id,
                    "trigger": {
                        "reason": reason,
                        "command_id": command_id,
                    },
                    "profile_id": profile_id,
                    "rgb_controls": pair.rgb.controls,
                    "nir_controls": pair.nir.controls,
                    "rgb_sensor_timestamp_ns": pair.rgb.sensor_timestamp_ns,
                    "nir_sensor_timestamp_ns": pair.nir.sensor_timestamp_ns,
                    "registration": registration,
                    "environment": environment,
                    "device_quality": {
                        "rgb": rgb_quality.as_dict(),
                        "nir": nir_quality.as_dict(),
                        "attempt": attempt,
                    },
                }
                self.queue.enqueue(
                    capture_id=capture_id,
                    captured_at=pair.rgb.captured_at.isoformat(),
                    sync_delta_ms=pair.sync_delta_ms,
                    metadata=metadata,
                    rgb_data=pair.rgb.data,
                    nir_data=aligned_nir,
                    command_id=command_id,
                )
                LOGGER.info("Queued capture %s (%s)", capture_id, reason)
                return capture_id
            except DeviceImageError as exc:
                last_error = exc
                LOGGER.warning(
                    "Capture quality attempt %s/%s failed: %s",
                    attempt + 1,
                    self.config.capture_retry_count + 1,
                    exc,
                )
        assert last_error is not None
        raise last_error

    def flush_queue(self) -> list[str]:
        uploaded: list[str] = []
        for item in self.queue.ready():
            command_id = item.manifest.get("command_id")
            try:
                if item.manifest.get("status") == "uploaded":
                    remote_capture_id = str(item.manifest["remote_capture_id"])
                else:
                    response = self.backend.upload_capture(item)
                    remote_capture_id = str(response["id"])
                    item = self.queue.mark_upload_succeeded(item, remote_capture_id)

                if command_id:
                    self.backend.complete_command(
                        str(command_id),
                        status="completed",
                        capture_id=remote_capture_id,
                        message="Capture uploaded",
                    )
                self.queue.acknowledge(item)
                uploaded.append(remote_capture_id)
                LOGGER.info("Uploaded capture %s", remote_capture_id)
            except RetryableApiError as exc:
                self.queue.mark_failure(item, str(exc))
                LOGGER.warning("Upload deferred for %s: %s", item.capture_id, exc)
                break
            except NonRetryableApiError as exc:
                self.queue.mark_rejected(item, str(exc))
                if command_id:
                    try:
                        self.backend.complete_command(
                            str(command_id),
                            status="failed",
                            capture_id=None,
                            message=str(exc),
                        )
                    except (RetryableApiError, NonRetryableApiError):
                        LOGGER.exception("Could not mark command %s failed", command_id)
                LOGGER.error("Capture %s rejected: %s", item.capture_id, exc)
        return uploaded

    def process_next_command(self) -> str | None:
        command = self.backend.claim_command()
        if command is None:
            return None
        command_id = str(command["id"])
        try:
            if command["type"] != "capture_now":
                raise ValueError(f"Unsupported command type {command['type']}")
            capture_id = self.capture(reason="remote", command_id=command_id)
            self.flush_queue()
            return capture_id
        except Exception as exc:
            LOGGER.exception("Command %s failed", command_id)
            try:
                self.backend.complete_command(
                    command_id,
                    status="failed",
                    capture_id=None,
                    message=str(exc),
                )
            except (RetryableApiError, NonRetryableApiError):
                LOGGER.exception("Could not report command %s failure", command_id)
            return None

    def process_preview(self) -> dict[str, Any] | None:
        request = self.backend.get_preview_request()
        if not request.get("active"):
            self.preview_session_id = None
            self.next_preview_at = 0.0
            return None

        session_id = str(request["session_id"])
        if self.preview_session_id != session_id:
            self.preview_session_id = session_id
            self.next_preview_at = 0.0
        now = time.time()
        if now < self.next_preview_at:
            return None

        profile_response = self.refresh_profile()
        profile = profile_response["profile"]
        environment = self.sensors.read()
        profile_id = select_exposure_profile(
            profile,
            environment.get("illuminance_lux"),
        )
        pair = self.cameras.capture(profile, profile_id)
        aligned_nir, _ = self.registrar.align_nir(
            pair.rgb.data,
            pair.nir.data,
        )
        maximum_width = int(request.get("preview_width", 960))
        rgb_preview = resize_preview_jpeg(pair.rgb.data, maximum_width)
        nir_preview = resize_preview_jpeg(aligned_nir, maximum_width)
        response = self.backend.upload_preview(
            session_id=session_id,
            captured_at=pair.rgb.captured_at.isoformat(),
            sync_delta_ms=pair.sync_delta_ms,
            rgb_data=rgb_preview,
            nir_data=nir_preview,
        )
        self.next_preview_at = time.time() + float(
            request.get("interval_seconds", 2.0)
        )
        LOGGER.debug(
            "Uploaded preview frame %s for session %s",
            response.get("sequence"),
            session_id,
        )
        return response

    def send_heartbeat(self) -> None:
        usage = shutil.disk_usage(self.config.queue_path)
        used_percent = 100.0 * (usage.total - usage.free) / usage.total
        try:
            ip_address = socket.gethostbyname(socket.gethostname())
        except OSError:
            ip_address = None
        self.backend.heartbeat(
            {
                "status": "online",
                "ip_address": ip_address,
                "firmware_version": self.config.firmware_version,
                "queue_depth": self.queue.depth(),
                "storage_used_percent": round(used_percent, 2),
            }
        )

    def run_once(self, *, reason: str = "manual") -> str:
        self.refresh_profile(force=True)
        capture_id = self.capture(reason=reason)
        self.flush_queue()
        self.send_heartbeat()
        return capture_id

    def run_forever(self) -> None:
        self.refresh_profile(force=True)
        now = time.time()
        next_capture = (
            now
            if self.config.capture_on_start
            else self._next_capture_time(now)
        )
        next_heartbeat = now

        while True:
            now = time.time()
            try:
                previous_interval = self.interval_minutes
                self.refresh_profile()
                if self.interval_minutes != previous_interval:
                    next_capture = self._next_capture_time(now)
                self.flush_queue()
                self.process_next_command()
                self.process_preview()

                if now >= next_capture:
                    self.capture(reason="scheduled")
                    self.flush_queue()
                    next_capture = self._next_capture_time(time.time())

                if now >= next_heartbeat:
                    self.send_heartbeat()
                    next_heartbeat = now + self.config.heartbeat_seconds
            except (RetryableApiError, OSError) as exc:
                LOGGER.warning("Temporary device loop error: %s", exc)
            except Exception:
                LOGGER.exception("Unexpected device loop error")
            time.sleep(self.config.poll_seconds)

    @property
    def interval_minutes(self) -> int:
        profile = self.profile_response or {}
        return int(profile.get("capture_interval_minutes", 15))

    def _next_capture_time(self, now: float) -> float:
        interval_seconds = self.interval_minutes * 60
        if not self.config.align_to_interval:
            return now + interval_seconds
        return ((int(now) // interval_seconds) + 1) * interval_seconds

    def _write_profile_cache(self, profile: dict[str, Any]) -> None:
        temporary = self.profile_cache_path.with_suffix(".json.part")
        temporary.write_text(
            json.dumps(profile, separators=(",", ":"), sort_keys=True),
            encoding="utf-8",
        )
        os.replace(temporary, self.profile_cache_path)

    def close(self) -> None:
        self.cameras.close()
        self.backend.close()
