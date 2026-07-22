from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import cv2
import numpy as np


class DeviceImageError(ValueError):
    pass


@dataclass(frozen=True)
class QualityMetrics:
    width: int
    height: int
    blur_score: float
    mean_normalized: float
    dark_fraction: float
    saturated_fraction: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def decode_image(data: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise DeviceImageError("Captured image could not be decoded")
    return image


def encode_jpeg(image: np.ndarray, quality: int = 92) -> bytes:
    ok, encoded = cv2.imencode(
        ".jpg",
        image,
        [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)],
    )
    if not ok:
        raise DeviceImageError("JPEG encoding failed")
    return encoded.tobytes()


def analyze(data: bytes) -> QualityMetrics:
    image = decode_image(data)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return QualityMetrics(
        width=int(image.shape[1]),
        height=int(image.shape[0]),
        blur_score=float(cv2.Laplacian(gray, cv2.CV_64F).var()),
        mean_normalized=float(gray.mean() / 255.0),
        dark_fraction=float(np.mean(gray <= 12)),
        saturated_fraction=float(np.mean(gray >= 250)),
    )


def validate_pair(
    rgb_data: bytes,
    nir_data: bytes,
    profile: dict[str, Any],
) -> tuple[QualityMetrics, QualityMetrics, list[str]]:
    rgb = analyze(rgb_data)
    nir = analyze(nir_data)
    failures: list[str] = []
    expected = profile["resolution"]
    expected_size = (int(expected["width"]), int(expected["height"]))
    quality = profile["quality"]

    for name, metrics in (("RGB", rgb), ("NIR", nir)):
        if (metrics.width, metrics.height) != expected_size:
            failures.append(
                f"{name} resolution {metrics.width}x{metrics.height} does not match "
                f"{expected_size[0]}x{expected_size[1]}"
            )
        if metrics.blur_score < float(quality["minimum_blur_score"]):
            failures.append(f"{name} blur score is below the configured minimum")
        if metrics.mean_normalized < float(quality["minimum_mean"]):
            failures.append(f"{name} is underexposed")
        if metrics.mean_normalized > float(quality["maximum_mean"]):
            failures.append(f"{name} is overexposed")
        if metrics.dark_fraction > float(quality["maximum_dark_fraction"]):
            failures.append(f"{name} dark-pixel fraction is too high")
        if metrics.saturated_fraction > float(quality["maximum_saturated_fraction"]):
            failures.append(f"{name} saturated-pixel fraction is too high")

    if failures:
        raise DeviceImageError("; ".join(failures))
    return rgb, nir, failures
