from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol


class SensorSuite(Protocol):
    def read(self) -> dict[str, Any]:
        ...


class NullSensorSuite:
    def read(self) -> dict[str, Any]:
        return {}


class SimulatedSensorSuite:
    def __init__(self, illuminance_lux: float) -> None:
        self.illuminance_lux = illuminance_lux

    def read(self) -> dict[str, Any]:
        sampled_at = datetime.now(timezone.utc).isoformat()
        return {
            "air_temperature_c": 24.5,
            "relative_humidity_percent": 68.0,
            "illuminance_lux": self.illuminance_lux,
            "sampled_at": sampled_at,
            "simulation": True,
        }
