from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timedelta, timezone

import cv2
import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .image_processing import (
    analyze_image,
    compute_ndvi,
    encode_jpeg,
    make_thumbnail,
    sha256_bytes,
)
from .models import Capture, Device
from .profiles import default_capture_profile
from .storage import Storage


def seed_demo_data(db: Session, storage: Storage) -> None:
    if db.scalar(select(func.count(Device.id))) or 0:
        return

    now = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
    profile = default_capture_profile()
    profile_json = json.dumps(profile, separators=(",", ":"))

    devices = [
        Device(
            id="field-node-01",
            name="Canopy Node 01",
            site_name="North Research Plot",
            status="online",
            last_seen_at=now - timedelta(minutes=2),
            wifi_ssid="FieldNet-5G",
            wifi_rssi_dbm=-58,
            ip_address="192.168.20.41",
            firmware_version="0.1.0",
            calibration_id="CAL-2026-07-A",
            capture_interval_minutes=15,
            queue_depth=0,
            storage_used_percent=18.6,
            battery_percent=84,
            latitude=12.9716,
            longitude=77.5946,
            profile_json=profile_json,
        ),
        Device(
            id="field-node-02",
            name="Canopy Node 02",
            site_name="East Orchard",
            status="attention",
            last_seen_at=now - timedelta(minutes=34),
            wifi_ssid="OrchardMesh",
            wifi_rssi_dbm=-76,
            ip_address="192.168.30.18",
            firmware_version="0.1.0",
            calibration_id="CAL-2026-07-B",
            capture_interval_minutes=30,
            queue_depth=7,
            storage_used_percent=41.2,
            battery_percent=61,
            latitude=12.9731,
            longitude=77.6012,
            profile_json=profile_json,
        ),
        Device(
            id="field-node-03",
            name="Wetland Node",
            site_name="South Wetland Edge",
            status="offline",
            last_seen_at=now - timedelta(hours=7, minutes=18),
            wifi_ssid=None,
            wifi_rssi_dbm=None,
            ip_address=None,
            firmware_version="0.0.9",
            calibration_id="CAL-2026-06-C",
            capture_interval_minutes=30,
            queue_depth=23,
            storage_used_percent=63.9,
            battery_percent=38,
            latitude=12.9638,
            longitude=77.5904,
            profile_json=profile_json,
        ),
    ]
    db.add_all(devices)
    db.commit()

    capture_specs: list[tuple[str, datetime, float, int, str]] = []
    growth_values = [0.31, 0.35, 0.39, 0.44, 0.48, 0.53, 0.57, 0.61]
    for index, growth in enumerate(growth_values):
        days_ago = 7 - index
        capture_time = (now - timedelta(days=days_ago)).replace(
            hour=6 + (index % 2) * 5,
            minute=30,
            second=0,
        )
        quality = "warning" if index == 2 else "pass"
        capture_specs.append(("field-node-01", capture_time, growth, index + 11, quality))

    for index, growth in enumerate([0.42, 0.46, 0.49]):
        capture_time = (now - timedelta(days=4 - index)).replace(
            hour=8,
            minute=15,
            second=0,
        )
        capture_specs.append(("field-node-02", capture_time, growth, index + 31, "pass"))

    for device_id, captured_at, growth, seed, quality_state in capture_specs:
        rgb_bytes, nir_bytes = generate_demo_pair(growth=growth, seed=seed)
        metrics_rgb = analyze_image(rgb_bytes)
        metrics_nir = analyze_image(nir_bytes)
        ndvi = compute_ndvi(rgb_bytes, nir_bytes, profile["ndvi_calibration"])
        capture_id = str(uuid.uuid4())
        date_key = captured_at.date().isoformat()
        prefix = f"captures/{date_key}/{capture_id}"

        rgb_key = f"{prefix}/rgb.jpg"
        nir_key = f"{prefix}/nir.jpg"
        ndvi_key = f"{prefix}/ndvi.png"
        rgb_thumb_key = f"{prefix}/rgb-thumb.jpg"
        nir_thumb_key = f"{prefix}/nir-thumb.jpg"
        ndvi_thumb_key = f"{prefix}/ndvi-thumb.jpg"

        storage.put_bytes(rgb_key, rgb_bytes, "image/jpeg")
        storage.put_bytes(nir_key, nir_bytes, "image/jpeg")
        storage.put_bytes(ndvi_key, ndvi.heatmap_png, "image/png")
        storage.put_bytes(rgb_thumb_key, make_thumbnail(rgb_bytes), "image/jpeg")
        storage.put_bytes(nir_thumb_key, make_thumbnail(nir_bytes), "image/jpeg")
        storage.put_bytes(ndvi_thumb_key, make_thumbnail(ndvi.heatmap_png), "image/jpeg")

        sync_delta = 1580.0 if quality_state == "warning" else 380.0 + seed * 3.0
        flags = ["sync_near_limit"] if quality_state == "warning" else []
        capture = Capture(
            id=capture_id,
            device_id=device_id,
            captured_at=captured_at,
            date_key=date_key,
            source="demo",
            status="accepted",
            quality_state=quality_state,
            sync_delta_ms=sync_delta,
            rgb_key=rgb_key,
            nir_key=nir_key,
            ndvi_key=ndvi_key,
            ndvi_data_key=None,
            rgb_thumb_key=rgb_thumb_key,
            nir_thumb_key=nir_thumb_key,
            ndvi_thumb_key=ndvi_thumb_key,
            rgb_width=metrics_rgb.width,
            rgb_height=metrics_rgb.height,
            rgb_blur_score=metrics_rgb.blur_score,
            nir_blur_score=metrics_nir.blur_score,
            rgb_mean=metrics_rgb.mean_normalized,
            nir_mean=metrics_nir.mean_normalized,
            saturated_fraction=max(
                metrics_rgb.saturated_fraction,
                metrics_nir.saturated_fraction,
            ),
            mean_ndvi=ndvi.mean,
            min_ndvi=ndvi.minimum,
            max_ndvi=ndvi.maximum,
            healthy_fraction=ndvi.healthy_fraction,
            stressed_fraction=ndvi.stressed_fraction,
            bare_fraction=ndvi.bare_fraction,
            quality_flags_json=json.dumps(flags),
            metadata_json=json.dumps(
                {
                    "demo": True,
                    "calibration_id": (
                        "CAL-2026-07-A"
                        if device_id == "field-node-01"
                        else "CAL-2026-07-B"
                    ),
                    "profile_id": "overcast",
                    "phenology_stage": demo_stage(growth),
                }
            ),
            rgb_sha256=sha256_bytes(rgb_bytes),
            nir_sha256=sha256_bytes(nir_bytes),
        )
        db.add(capture)
        db.commit()


def demo_stage(growth: float) -> str:
    if growth < 0.36:
        return "emergence"
    if growth < 0.48:
        return "vegetative"
    if growth < 0.58:
        return "canopy-development"
    return "mature-canopy"


def generate_demo_pair(growth: float, seed: int) -> tuple[bytes, bytes]:
    rng = np.random.default_rng(seed)
    width, height = 1280, 720
    y, x = np.mgrid[0:height, 0:width]

    vertical = y / max(height - 1, 1)
    horizontal = x / max(width - 1, 1)
    soil_texture = rng.normal(0, 1, (height, width)).astype(np.float32)
    soil_texture = cv2.GaussianBlur(soil_texture, (0, 0), 2.2)
    broad_texture = cv2.GaussianBlur(
        rng.normal(0, 1, (height, width)).astype(np.float32),
        (0, 0),
        35,
    )

    rgb = np.zeros((height, width, 3), dtype=np.float32)
    rgb[:, :, 0] = 68 + 14 * broad_texture + 12 * vertical
    rgb[:, :, 1] = 84 + 10 * broad_texture + 8 * vertical
    rgb[:, :, 2] = 116 + 12 * broad_texture + 10 * vertical

    mask = np.zeros((height, width), dtype=np.uint8)
    vanishing_x = width // 2 + int(math.sin(seed) * 55)
    row_count = 31
    base_half_span = int(width * 0.72)
    top_y = -20
    bottom_y = height + 30
    thickness = int(10 + growth * 42)
    for row_index in range(-row_count // 2, row_count // 2 + 1):
        bottom_x = vanishing_x + int(row_index * base_half_span / (row_count / 2))
        top_x = vanishing_x + int(row_index * 7)
        cv2.line(mask, (top_x, top_y), (bottom_x, bottom_y), 255, thickness)

    patch = cv2.GaussianBlur(
        rng.uniform(0, 1, (height, width)).astype(np.float32),
        (0, 0),
        22,
    )
    patch = cv2.normalize(patch, None, 0.72, 1.0, cv2.NORM_MINMAX)
    vegetation = (mask.astype(np.float32) / 255.0) * patch
    vegetation *= 0.68 + 0.32 * np.sin(horizontal * 5.4 + vertical * 2.1 + seed)
    canopy_spread = cv2.GaussianBlur(
        mask.astype(np.float32) / 255.0,
        (0, 0),
        5.0 + growth * 15.0,
    )
    vegetation = np.maximum(vegetation, canopy_spread * growth * 0.92)
    vegetation = np.clip(vegetation, 0, 1)

    green = 82 + growth * 74 + soil_texture * 8
    blue = 38 + growth * 24 + soil_texture * 5
    red = 47 + (1.0 - growth) * 27 + soil_texture * 6
    alpha = np.clip(vegetation * (0.78 + growth * 0.74), 0, 1)
    rgb[:, :, 0] = rgb[:, :, 0] * (1 - alpha) + blue * alpha
    rgb[:, :, 1] = rgb[:, :, 1] * (1 - alpha) + green * alpha
    rgb[:, :, 2] = rgb[:, :, 2] * (1 - alpha) + red * alpha

    # Add two compacted soil tracks and a slight illumination gradient.
    for offset in (-0.18, 0.24):
        center = int(width * (0.5 + offset))
        cv2.line(
            rgb,
            (vanishing_x + int(offset * 30), 0),
            (center, height),
            (58, 74, 106),
            14,
        )
    light = 0.92 + 0.13 * horizontal - 0.05 * vertical
    rgb *= light[:, :, None]

    nir_base = 108 + 8 * broad_texture + 6 * vertical
    nir_canopy = 195 + growth * 90 + soil_texture * 7
    nir = nir_base * (1 - alpha) + nir_canopy * alpha
    nir += 5 * np.sin(x / 33.0 + seed)
    nir = np.clip(nir, 0, 244).astype(np.uint8)
    nir_bgr = cv2.merge([nir, nir, nir])

    rgb = np.clip(rgb, 0, 244).astype(np.uint8)
    full_size = (4608, 2592)
    rgb = cv2.resize(rgb, full_size, interpolation=cv2.INTER_CUBIC)
    nir_bgr = cv2.resize(nir_bgr, full_size, interpolation=cv2.INTER_CUBIC)

    # Fine sensor-like texture keeps demo imagery crisp after enlargement.
    noise_shape = (2592, 4608)
    fine_noise = rng.integers(-9, 10, noise_shape, dtype=np.int16)
    rgb = np.clip(rgb.astype(np.int16) + fine_noise[:, :, None], 0, 255).astype(np.uint8)
    nir_bgr = np.clip(
        nir_bgr.astype(np.int16) + fine_noise[:, :, None],
        0,
        255,
    ).astype(np.uint8)
    return encode_jpeg(rgb, quality=86), encode_jpeg(nir_bgr, quality=86)
