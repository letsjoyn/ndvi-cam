from __future__ import annotations

import json
from typing import Any, Protocol

import httpx

from .models import QueueItem


class RetryableApiError(RuntimeError):
    pass


class NonRetryableApiError(RuntimeError):
    pass


class DeviceBackend(Protocol):
    def get_profile(self) -> dict[str, Any]:
        ...

    def upload_capture(self, item: QueueItem) -> dict[str, Any]:
        ...

    def heartbeat(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    def claim_command(self) -> dict[str, Any] | None:
        ...

    def complete_command(
        self,
        command_id: str,
        *,
        status: str,
        capture_id: str | None,
        message: str | None,
    ) -> dict[str, Any]:
        ...

    def get_preview_request(self) -> dict[str, Any]:
        ...

    def upload_preview(
        self,
        *,
        session_id: str,
        captured_at: str,
        sync_delta_ms: float,
        rgb_data: bytes,
        nir_data: bytes,
    ) -> dict[str, Any]:
        ...

    def close(self) -> None:
        ...


class FieldScopeApi:
    def __init__(
        self,
        base_url: str,
        device_id: str,
        device_key: str,
        *,
        verify_tls: bool = True,
    ) -> None:
        self.device_id = device_id
        headers = {"X-Device-Key": device_key} if device_key else {}
        self.client = httpx.Client(
            base_url=base_url,
            headers=headers,
            timeout=httpx.Timeout(60.0, connect=10.0),
            verify=verify_tls,
        )

    def get_profile(self) -> dict[str, Any]:
        response = self._request(
            "GET",
            f"/api/devices/{self.device_id}/capture-profile"
        )
        self._raise_for_status(response)
        return response.json()

    def upload_capture(self, item: QueueItem) -> dict[str, Any]:
        with item.rgb_path.open("rb") as rgb, item.nir_path.open("rb") as nir:
            response = self._request(
                "POST",
                "/api/captures",
                data={
                    "capture_id": item.capture_id,
                    "device_id": self.device_id,
                    "captured_at": item.manifest["captured_at"],
                    "source": "device",
                    "sync_delta_ms": str(item.manifest["sync_delta_ms"]),
                    "metadata": json.dumps(
                        item.manifest["metadata"],
                        separators=(",", ":"),
                    ),
                },
                files={
                    "rgb": ("rgb.jpg", rgb, "image/jpeg"),
                    "nir": ("nir.jpg", nir, "image/jpeg"),
                },
            )
        self._raise_for_status(response)
        return response.json()

    def heartbeat(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._request(
            "POST",
            f"/api/devices/{self.device_id}/heartbeat",
            json=payload,
        )
        self._raise_for_status(response)
        return response.json()

    def claim_command(self) -> dict[str, Any] | None:
        response = self._request(
            "POST",
            f"/api/devices/{self.device_id}/commands/claim"
        )
        self._raise_for_status(response)
        return response.json()

    def complete_command(
        self,
        command_id: str,
        *,
        status: str,
        capture_id: str | None,
        message: str | None,
    ) -> dict[str, Any]:
        response = self._request(
            "POST",
            f"/api/devices/{self.device_id}/commands/{command_id}/complete",
            json={
                "status": status,
                "capture_id": capture_id,
                "message": message,
            },
        )
        self._raise_for_status(response)
        return response.json()

    def get_preview_request(self) -> dict[str, Any]:
        response = self._request(
            "GET",
            f"/api/devices/{self.device_id}/preview/request",
        )
        self._raise_for_status(response)
        return response.json()

    def upload_preview(
        self,
        *,
        session_id: str,
        captured_at: str,
        sync_delta_ms: float,
        rgb_data: bytes,
        nir_data: bytes,
    ) -> dict[str, Any]:
        response = self._request(
            "POST",
            f"/api/devices/{self.device_id}/preview/frame",
            data={
                "session_id": session_id,
                "captured_at": captured_at,
                "sync_delta_ms": str(sync_delta_ms),
            },
            files={
                "rgb": ("rgb-preview.jpg", rgb_data, "image/jpeg"),
                "nir": ("nir-preview.jpg", nir_data, "image/jpeg"),
            },
        )
        self._raise_for_status(response)
        return response.json()

    def close(self) -> None:
        self.client.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            return self.client.request(method, path, **kwargs)
        except httpx.RequestError as exc:
            raise RetryableApiError(str(exc)) from exc

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.is_success:
            return
        try:
            payload = response.json()
            detail = payload.get("detail", payload)
            if isinstance(detail, dict):
                message = str(detail.get("message", detail))
            else:
                message = str(detail)
        except ValueError:
            message = response.text or f"HTTP {response.status_code}"
        if response.status_code >= 500 or response.status_code in {408, 429}:
            raise RetryableApiError(message)
        raise NonRetryableApiError(message)
