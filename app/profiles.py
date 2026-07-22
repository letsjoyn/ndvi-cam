from __future__ import annotations

from copy import deepcopy


DEFAULT_CAPTURE_PROFILE = {
    "schema_version": "1.0.0",
    "locked": True,
    "resolution": {
        "width": 4608,
        "height": 2592,
    },
    "maximum_sync_delta_ms": 2000,
    "quality": {
        "minimum_blur_score": 55.0,
        "minimum_mean": 0.03,
        "maximum_mean": 0.92,
        "maximum_dark_fraction": 0.55,
        "maximum_saturated_fraction": 0.02,
    },
    "control_tolerance": {
        "lens_position": 0.05,
        "colour_gain": 0.03,
        "exposure_us": 50,
        "analogue_gain": 0.05,
    },
    "cameras": {
        "rgb": {
            "model": "Raspberry Pi Camera Module 3",
            "ae_enabled": False,
            "awb_enabled": False,
            "lens_position": 3.2,
            "colour_gains": [1.75, 1.55],
            "scaler_crop": [0, 0, 4608, 2592],
            "exposure_profiles": {
                "bright": {
                    "minimum_lux": 30000,
                    "exposure_us": 1000,
                    "analogue_gain": 1.0,
                },
                "overcast": {
                    "minimum_lux": 3000,
                    "exposure_us": 4000,
                    "analogue_gain": 1.0,
                },
                "low_light": {
                    "minimum_lux": 50,
                    "exposure_us": 15000,
                    "analogue_gain": 2.0,
                },
            },
        },
        "nir": {
            "model": "Raspberry Pi Camera Module 3 NoIR",
            "filter": "850 nm band-pass",
            "ae_enabled": False,
            "awb_enabled": False,
            "lens_position": 3.6,
            "colour_gains": [1.0, 1.0],
            "scaler_crop": [0, 0, 4608, 2592],
            "exposure_profiles": {
                "bright": {
                    "minimum_lux": 30000,
                    "exposure_us": 3000,
                    "analogue_gain": 1.0,
                },
                "overcast": {
                    "minimum_lux": 3000,
                    "exposure_us": 8000,
                    "analogue_gain": 1.5,
                },
                "low_light": {
                    "minimum_lux": 50,
                    "exposure_us": 25000,
                    "analogue_gain": 2.5,
                },
            },
        },
    },
    "ndvi_calibration": {
        "red_scale": 1.0,
        "red_offset": 0.0,
        "nir_scale": 1.0,
        "nir_offset": 0.0,
    },
}


def default_capture_profile() -> dict:
    return deepcopy(DEFAULT_CAPTURE_PROFILE)

