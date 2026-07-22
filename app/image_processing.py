from __future__ import annotations

import hashlib
import io
from dataclasses import asdict, dataclass
from typing import Any

import cv2
import numpy as np


class ImageValidationError(ValueError):
    pass


ASPECT_RATIO_TOLERANCE = 0.02


@dataclass(frozen=True)
class ImageMetrics:
    width: int
    height: int
    blur_score: float
    mean_normalized: float
    dark_fraction: float
    saturated_fraction: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NdviResult:
    heatmap_png: bytes
    data_npz: bytes
    mean: float
    minimum: float
    maximum: float
    healthy_fraction: float
    stressed_fraction: float
    bare_fraction: float


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode_image(data: bytes) -> np.ndarray:
    buffer = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise ImageValidationError("The uploaded file is not a decodable image")
    return image


def encode_jpeg(image: np.ndarray, quality: int = 88) -> bytes:
    ok, encoded = cv2.imencode(
        ".jpg",
        image,
        [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)],
    )
    if not ok:
        raise ImageValidationError("JPEG encoding failed")
    return encoded.tobytes()


def encode_png(image: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(
        ".png",
        image,
        [int(cv2.IMWRITE_PNG_COMPRESSION), 5],
    )
    if not ok:
        raise ImageValidationError("PNG encoding failed")
    return encoded.tobytes()


def analyze_image(data: bytes) -> ImageMetrics:
    image = decode_image(data)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return ImageMetrics(
        width=int(image.shape[1]),
        height=int(image.shape[0]),
        blur_score=float(cv2.Laplacian(gray, cv2.CV_64F).var()),
        mean_normalized=float(gray.mean() / 255.0),
        dark_fraction=float(np.mean(gray <= 12)),
        saturated_fraction=float(np.mean(gray >= 250)),
    )


def make_thumbnail(data: bytes, width: int = 560) -> bytes:
    image = decode_image(data)
    if image.shape[1] <= width:
        return encode_jpeg(image, quality=84)
    height = max(1, round(image.shape[0] * width / image.shape[1]))
    resized = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
    return encode_jpeg(resized, quality=84)


def aspect_ratios_match(
    first_width: int,
    first_height: int,
    second_width: int,
    second_height: int,
) -> bool:
    first_ratio = first_width / first_height
    second_ratio = second_width / second_height
    relative_difference = abs(first_ratio - second_ratio) / first_ratio
    return relative_difference <= ASPECT_RATIO_TOLERANCE


def validate_pair(
    rgb_data: bytes,
    nir_data: bytes,
    profile: dict[str, Any],
    *,
    strict_resolution: bool,
    sync_delta_ms: float | None,
    metadata: dict[str, Any],
) -> tuple[ImageMetrics, ImageMetrics, list[str]]:
    rgb = analyze_image(rgb_data)
    nir = analyze_image(nir_data)
    quality = profile["quality"]
    flags: list[str] = []
    failures: list[str] = []

    if (rgb.width, rgb.height) != (nir.width, nir.height):
        dimensions = (
            f"RGB is {rgb.width}x{rgb.height}; NIR is {nir.width}x{nir.height}"
        )
        if strict_resolution:
            failures.append(
                f"{dimensions}. Device captures must use identical dimensions"
            )
        elif aspect_ratios_match(
            rgb.width,
            rgb.height,
            nir.width,
            nir.height,
        ):
            flags.append("nir_resampled_to_rgb")
        else:
            failures.append(
                f"{dimensions}. Their aspect ratios differ; crop both images "
                "to the same scene framing before upload"
            )

    expected = profile["resolution"]
    if strict_resolution and (rgb.width, rgb.height) != (
        int(expected["width"]),
        int(expected["height"]),
    ):
        failures.append(
            f"Expected {expected['width']}x{expected['height']} images, "
            f"received {rgb.width}x{rgb.height}"
        )

    for name, metrics in (("RGB", rgb), ("NIR", nir)):
        if metrics.blur_score < float(quality["minimum_blur_score"]):
            failures.append(
                f"{name} blur score {metrics.blur_score:.1f} is below "
                f"{quality['minimum_blur_score']}"
            )
        if metrics.mean_normalized < float(quality["minimum_mean"]):
            failures.append(f"{name} image is underexposed")
        if metrics.mean_normalized > float(quality["maximum_mean"]):
            failures.append(f"{name} image is overexposed")
        if metrics.dark_fraction > float(quality["maximum_dark_fraction"]):
            failures.append(f"{name} dark-pixel fraction is too high")
        if metrics.saturated_fraction > float(quality["maximum_saturated_fraction"]):
            if strict_resolution:
                failures.append(f"{name} saturated-pixel fraction is too high")
            else:
                flags.append(f"{name.lower()}_saturation_high")

    maximum_delta = float(profile["maximum_sync_delta_ms"])
    if sync_delta_ms is None:
        flags.append("sync_delta_missing")
    elif sync_delta_ms > maximum_delta:
        failures.append(
            f"RGB/NIR capture delta {sync_delta_ms:.1f} ms exceeds {maximum_delta:.1f} ms"
        )

    if metadata:
        failures.extend(validate_fixed_controls(profile, metadata))
    else:
        flags.append("camera_controls_missing")

    if failures:
        raise ImageValidationError("; ".join(failures))
    return rgb, nir, flags


def validate_fixed_controls(
    profile: dict[str, Any],
    metadata: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    tolerance = profile["control_tolerance"]

    for camera_name in ("rgb", "nir"):
        actual = metadata.get(f"{camera_name}_controls")
        expected = profile["cameras"][camera_name]
        if not isinstance(actual, dict):
            failures.append(f"{camera_name.upper()} camera controls are missing")
            continue

        if actual.get("ae_enabled") is not False:
            failures.append(f"{camera_name.upper()} automatic exposure must be disabled")
        if actual.get("awb_enabled") is not False:
            failures.append(f"{camera_name.upper()} automatic white balance must be disabled")

        actual_crop = actual.get("scaler_crop")
        if actual_crop != expected["scaler_crop"]:
            failures.append(f"{camera_name.upper()} scaler crop/zoom changed")

        lens = actual.get("lens_position")
        if lens is None or abs(float(lens) - float(expected["lens_position"])) > float(
            tolerance["lens_position"]
        ):
            failures.append(f"{camera_name.upper()} focus position drifted")

        gains = actual.get("colour_gains")
        expected_gains = expected["colour_gains"]
        if not isinstance(gains, list) or len(gains) != 2:
            failures.append(f"{camera_name.upper()} colour gains are missing")
        elif any(
            abs(float(value) - float(expected_value))
            > float(tolerance["colour_gain"])
            for value, expected_value in zip(gains, expected_gains, strict=True)
        ):
            failures.append(f"{camera_name.upper()} white-balance gains drifted")

        profile_id = actual.get("profile_id")
        exposure_profile = expected["exposure_profiles"].get(str(profile_id))
        if exposure_profile is None:
            failures.append(f"{camera_name.upper()} exposure profile is not approved")
            continue

        exposure = actual.get("exposure_us")
        gain = actual.get("analogue_gain")
        if exposure is None or abs(float(exposure) - float(exposure_profile["exposure_us"])) > float(
            tolerance["exposure_us"]
        ):
            failures.append(f"{camera_name.upper()} exposure time drifted")
        if gain is None or abs(float(gain) - float(exposure_profile["analogue_gain"])) > float(
            tolerance["analogue_gain"]
        ):
            failures.append(f"{camera_name.upper()} analogue gain drifted")

    return failures


def compute_ndvi(
    rgb_data: bytes,
    nir_data: bytes,
    calibration: dict[str, float] | None = None,
) -> NdviResult:
    rgb = decode_image(rgb_data)
    nir = decode_image(nir_data)
    if rgb.shape[:2] != nir.shape[:2]:
        rgb_height, rgb_width = rgb.shape[:2]
        nir_height, nir_width = nir.shape[:2]
        if not aspect_ratios_match(
            rgb_width,
            rgb_height,
            nir_width,
            nir_height,
        ):
            raise ImageValidationError(
                f"RGB is {rgb_width}x{rgb_height}; NIR is "
                f"{nir_width}x{nir_height}. Their aspect ratios differ"
            )
        interpolation = (
            cv2.INTER_AREA
            if nir_width > rgb_width or nir_height > rgb_height
            else cv2.INTER_CUBIC
        )
        nir = cv2.resize(
            nir,
            (rgb_width, rgb_height),
            interpolation=interpolation,
        )

    calibration = calibration or {}
    red_raw = rgb[:, :, 2].astype(np.float32) / 255.0
    nir_raw = cv2.cvtColor(nir, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    red = red_raw.copy()
    nir_gray = nir_raw.copy()
    red = red * float(calibration.get("red_scale", 1.0)) + float(
        calibration.get("red_offset", 0.0)
    )
    nir_gray = nir_gray * float(calibration.get("nir_scale", 1.0)) + float(
        calibration.get("nir_offset", 0.0)
    )

    denominator = nir_gray + red
    saturated = (red_raw >= (250.0 / 255.0)) | (nir_raw >= (250.0 / 255.0))
    valid = (denominator > 0.06) & ~saturated
    ndvi = np.zeros_like(red, dtype=np.float32)
    ndvi[valid] = (nir_gray[valid] - red[valid]) / denominator[valid]
    ndvi = np.clip(ndvi, -1.0, 1.0)

    values = ndvi[valid]
    if values.size == 0:
        raise ImageValidationError("No valid pixels were available for NDVI")

    heatmap = ndvi_to_heatmap(ndvi, valid)
    buffer = io.BytesIO()
    np.savez_compressed(buffer, ndvi=ndvi.astype(np.float32), valid=valid)

    return NdviResult(
        heatmap_png=encode_png(heatmap),
        data_npz=buffer.getvalue(),
        mean=float(values.mean()),
        minimum=float(values.min()),
        maximum=float(values.max()),
        healthy_fraction=float(np.mean(values >= 0.45)),
        stressed_fraction=float(np.mean((values >= 0.15) & (values < 0.45))),
        bare_fraction=float(np.mean(values < 0.15)),
    )


def ndvi_to_heatmap(ndvi: np.ndarray, valid: np.ndarray) -> np.ndarray:
    stops = np.array([-1.0, -0.2, 0.0, 0.2, 0.45, 0.7, 1.0], dtype=np.float32)
    # RGB colors: water/invalid brown, soil, yellow, light green, deep green.
    colors = np.array(
        [
            [59, 76, 92],
            [116, 78, 48],
            [190, 139, 62],
            [222, 195, 72],
            [137, 181, 73],
            [54, 132, 67],
            [20, 91, 50],
        ],
        dtype=np.float32,
    )

    flat = ndvi.ravel()
    rgb = np.empty((flat.size, 3), dtype=np.float32)
    for channel in range(3):
        rgb[:, channel] = np.interp(flat, stops, colors[:, channel])
    rgb = rgb.reshape((*ndvi.shape, 3)).astype(np.uint8)
    rgb[~valid] = np.array([224, 226, 229], dtype=np.uint8)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
