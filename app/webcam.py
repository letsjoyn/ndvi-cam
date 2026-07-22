from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Iterator

import cv2
import numpy as np

from .image_processing import encode_jpeg


class WebcamError(RuntimeError):
    pass


SUPPORTED_RESOLUTIONS = {
    (640, 480),
    (1280, 720),
    (1920, 1080),
}
SUPPORTED_FPS = {10, 15, 30}


class WebcamManager:
    def __init__(
        self,
        *,
        enabled: bool,
        camera_index: int,
        camera_name: str,
        width: int,
        height: int,
        fps: int,
        zoom: float,
    ) -> None:
        self.enabled = enabled
        self.camera_index = camera_index
        self.camera_name = camera_name
        self._width = width
        self._height = height
        self._fps = fps
        self._zoom = zoom

        self._lock = threading.RLock()
        self._frame_ready = threading.Condition(self._lock)
        self._stop_event = threading.Event()
        self._capture: cv2.VideoCapture | None = None
        self._thread: threading.Thread | None = None
        self._latest_frame: np.ndarray | None = None
        self._latest_frame_at: float | None = None
        self._active_width = 0
        self._active_height = 0
        self._active_fps = 0.0
        self._last_error: str | None = None
        self._running = False

    def start(self) -> dict[str, Any]:
        with self._lock:
            if not self.enabled:
                raise WebcamError("Webcam support is disabled")
            if self._running and self._thread and self._thread.is_alive():
                return self.status()
            if self._thread and self._thread.is_alive():
                raise WebcamError("The camera is still shutting down")

            self._stop_event = threading.Event()
            self._latest_frame = None
            self._latest_frame_at = None
            self._last_error = None

            backend = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY
            capture = cv2.VideoCapture(self.camera_index, backend)
            if not capture.isOpened():
                capture.release()
                self._last_error = (
                    f"Could not open camera index {self.camera_index}. "
                    "Check that it is connected and not in use by another application."
                )
                raise WebcamError(self._last_error)

            capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
            capture.set(cv2.CAP_PROP_FPS, self._fps)

            self._capture = capture
            self._active_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)) or self._width
            self._active_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) or self._height
            self._active_fps = float(capture.get(cv2.CAP_PROP_FPS)) or float(self._fps)
            self._running = True
            self._thread = threading.Thread(
                target=self._read_frames,
                args=(capture, self._stop_event),
                name="fieldscope-webcam",
                daemon=True,
            )
            self._thread.start()
            return self.status()

    def stop(self) -> None:
        with self._lock:
            thread = self._thread
            self._stop_event.set()
            self._running = False
            self._frame_ready.notify_all()

        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=3.0)
        if thread and thread.is_alive():
            with self._lock:
                self._last_error = "Timed out while stopping the camera"
            return
        with self._lock:
            if self._thread is thread:
                self._thread = None
            self._capture = None

    def configure(
        self,
        *,
        width: int,
        height: int,
        fps: int,
        zoom: float,
    ) -> dict[str, Any]:
        if (width, height) not in SUPPORTED_RESOLUTIONS:
            raise ValueError("Unsupported webcam resolution")
        if fps not in SUPPORTED_FPS:
            raise ValueError("Webcam FPS must be 10, 15, or 30")
        if zoom < 1.0 or zoom > 3.0:
            raise ValueError("Digital zoom must be between 1.0x and 3.0x")

        with self._lock:
            restart = (
                width != self._width
                or height != self._height
                or fps != self._fps
            )
            was_running = self._running
            self._width = width
            self._height = height
            self._fps = fps
            self._zoom = round(float(zoom), 2)

        if restart and was_running:
            self.stop()
            time.sleep(0.15)
            self.start()
        return self.status()

    def status(self) -> dict[str, Any]:
        with self._lock:
            frame = self._latest_frame.copy() if self._latest_frame is not None else None
            frame_at = self._latest_frame_at
            payload: dict[str, Any] = {
                "enabled": self.enabled,
                "running": self._running,
                "camera_index": self.camera_index,
                "camera_name": self.camera_name,
                "configured": {
                    "width": self._width,
                    "height": self._height,
                    "fps": self._fps,
                    "zoom": self._zoom,
                },
                "active": {
                    "width": self._active_width or self._width,
                    "height": self._active_height or self._height,
                    "fps": round(self._active_fps or float(self._fps), 2),
                },
                "frame": None,
                "error": self._last_error,
            }

        if frame is not None and frame_at is not None:
            processed = self._apply_zoom(frame)
            gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
            payload["frame"] = {
                "captured_at": datetime.fromtimestamp(
                    frame_at,
                    timezone.utc,
                ).isoformat(),
                "age_ms": round(max(0.0, time.time() - frame_at) * 1000.0, 1),
                "brightness": round(float(gray.mean() / 255.0), 4),
                "sharpness": round(
                    float(cv2.Laplacian(gray, cv2.CV_64F).var()),
                    2,
                ),
                "dark_fraction": round(float(np.mean(gray <= 12)), 5),
                "saturated_fraction": round(float(np.mean(gray >= 250)), 5),
            }
        return payload

    def capture_jpeg(self, timeout: float = 5.0) -> bytes:
        frame = self._wait_for_frame(timeout)
        return encode_jpeg(self._apply_zoom(frame), quality=92)

    def mjpeg_stream(self, maximum_fps: int = 10) -> Iterator[bytes]:
        self.start()
        delay = 1.0 / max(1, maximum_fps)
        while True:
            started = time.monotonic()
            with self._lock:
                if not self._running:
                    break
            try:
                jpeg = self.capture_jpeg(timeout=2.0)
            except WebcamError:
                break
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Cache-Control: no-cache\r\n\r\n"
                + jpeg
                + b"\r\n"
            )
            remaining = delay - (time.monotonic() - started)
            if remaining > 0:
                time.sleep(remaining)

    def _read_frames(
        self,
        capture: cv2.VideoCapture,
        stop_event: threading.Event,
    ) -> None:
        failures = 0
        while not stop_event.is_set():
            ok, frame = capture.read()
            if not ok or frame is None:
                failures += 1
                if failures >= 20:
                    with self._lock:
                        self._last_error = "The camera stopped returning frames"
                        self._running = False
                        self._frame_ready.notify_all()
                    break
                time.sleep(0.05)
                continue

            failures = 0
            with self._lock:
                self._latest_frame = frame
                self._latest_frame_at = time.time()
                self._active_width = int(frame.shape[1])
                self._active_height = int(frame.shape[0])
                self._frame_ready.notify_all()

        capture.release()
        with self._lock:
            if self._capture is capture:
                self._capture = None
            if self._thread is threading.current_thread():
                self._thread = None
            self._running = False
            self._frame_ready.notify_all()

    def _wait_for_frame(self, timeout: float) -> np.ndarray:
        self.start()
        deadline = time.monotonic() + timeout
        with self._frame_ready:
            while self._latest_frame is None and self._running:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._frame_ready.wait(timeout=remaining)
            if self._latest_frame is None:
                raise WebcamError(self._last_error or "Timed out waiting for a camera frame")
            return self._latest_frame.copy()

    def _apply_zoom(self, frame: np.ndarray) -> np.ndarray:
        with self._lock:
            zoom = self._zoom
        if zoom <= 1.0:
            return frame

        height, width = frame.shape[:2]
        crop_width = max(1, round(width / zoom))
        crop_height = max(1, round(height / zoom))
        left = (width - crop_width) // 2
        top = (height - crop_height) // 2
        cropped = frame[top : top + crop_height, left : left + crop_width]
        return cv2.resize(cropped, (width, height), interpolation=cv2.INTER_LINEAR)
