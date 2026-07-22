from __future__ import annotations

import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import QueueItem


class CaptureQueue:
    def __init__(
        self,
        root: Path,
        *,
        retry_base_seconds: float,
        retry_max_seconds: float,
    ) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.retry_base_seconds = retry_base_seconds
        self.retry_max_seconds = retry_max_seconds

    def enqueue(
        self,
        *,
        capture_id: str,
        captured_at: str,
        sync_delta_ms: float,
        metadata: dict[str, Any],
        rgb_data: bytes,
        nir_data: bytes,
        command_id: str | None,
    ) -> QueueItem:
        final_path = self._safe_path(capture_id)
        temporary_path = self._safe_path(f".{capture_id}.part")
        if final_path.exists():
            return self._load_item(final_path)
        if temporary_path.exists():
            shutil.rmtree(temporary_path)
        temporary_path.mkdir(parents=False)
        (temporary_path / "rgb.jpg").write_bytes(rgb_data)
        (temporary_path / "nir.jpg").write_bytes(nir_data)
        manifest = {
            "capture_id": capture_id,
            "captured_at": captured_at,
            "sync_delta_ms": sync_delta_ms,
            "metadata": metadata,
            "command_id": command_id,
            "status": "pending",
            "attempts": 0,
            "next_attempt_at": 0.0,
            "last_error": None,
            "remote_capture_id": None,
            "queued_at": datetime.now(timezone.utc).isoformat(),
        }
        self._write_json(temporary_path / "manifest.json", manifest)
        os.replace(temporary_path, final_path)
        return QueueItem(capture_id=capture_id, path=final_path, manifest=manifest)

    def ready(self, now: float | None = None) -> list[QueueItem]:
        current = time.time() if now is None else now
        items: list[QueueItem] = []
        for path in sorted(self.root.iterdir()):
            if not path.is_dir() or path.name.startswith("."):
                continue
            item = self._load_item(path)
            if item.manifest.get("status") not in {"pending", "uploaded"}:
                continue
            if float(item.manifest.get("next_attempt_at", 0.0)) <= current:
                items.append(item)
        return sorted(items, key=lambda item: item.manifest.get("queued_at", ""))

    def depth(self) -> int:
        return len(self.ready(now=float("inf")))

    def mark_upload_succeeded(self, item: QueueItem, remote_capture_id: str) -> QueueItem:
        manifest = dict(item.manifest)
        manifest["status"] = "uploaded"
        manifest["remote_capture_id"] = remote_capture_id
        manifest["last_error"] = None
        self._write_json(item.path / "manifest.json", manifest)
        return QueueItem(item.capture_id, item.path, manifest)

    def mark_failure(self, item: QueueItem, message: str) -> None:
        manifest = dict(item.manifest)
        attempts = int(manifest.get("attempts", 0)) + 1
        delay = min(
            self.retry_max_seconds,
            self.retry_base_seconds * (2 ** max(0, attempts - 1)),
        )
        manifest["attempts"] = attempts
        manifest["next_attempt_at"] = time.time() + delay
        manifest["last_error"] = message[:1000]
        self._write_json(item.path / "manifest.json", manifest)

    def mark_rejected(self, item: QueueItem, message: str) -> None:
        manifest = dict(item.manifest)
        manifest["status"] = "rejected"
        manifest["last_error"] = message[:1000]
        self._write_json(item.path / "manifest.json", manifest)

    def acknowledge(self, item: QueueItem) -> None:
        path = self._safe_path(item.capture_id)
        if path.exists():
            shutil.rmtree(path)

    def _load_item(self, path: Path) -> QueueItem:
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        return QueueItem(
            capture_id=str(manifest["capture_id"]),
            path=path,
            manifest=manifest,
        )

    def _safe_path(self, name: str) -> Path:
        path = (self.root / name).resolve()
        if path.parent != self.root:
            raise ValueError("Queue item escaped the queue root")
        return path

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        temporary = path.with_suffix(path.suffix + ".part")
        temporary.write_text(
            json.dumps(payload, separators=(",", ":"), sort_keys=True),
            encoding="utf-8",
        )
        os.replace(temporary, path)
