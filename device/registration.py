from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .quality import decode_image, encode_jpeg


@dataclass(frozen=True)
class PairRegistrar:
    calibration_id: str
    homography: np.ndarray | None
    source_path: str | None

    @classmethod
    def load(cls, path: Path | None) -> "PairRegistrar":
        if path is None:
            return cls(
                calibration_id="unregistered",
                homography=None,
                source_path=None,
            )
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        matrix = np.asarray(payload["nir_to_rgb_homography"], dtype=np.float64)
        if matrix.shape != (3, 3):
            raise ValueError("nir_to_rgb_homography must be a 3x3 matrix")
        return cls(
            calibration_id=str(payload["calibration_id"]),
            homography=matrix,
            source_path=str(path),
        )

    def align_nir(self, rgb_data: bytes, nir_data: bytes) -> tuple[bytes, dict[str, Any]]:
        rgb = decode_image(rgb_data)
        nir = decode_image(nir_data)
        output_size = (int(rgb.shape[1]), int(rgb.shape[0]))
        if self.homography is None:
            if nir.shape[:2] != rgb.shape[:2]:
                nir = cv2.resize(nir, output_size, interpolation=cv2.INTER_AREA)
            return encode_jpeg(nir), {
                "state": "not_calibrated",
                "calibration_id": self.calibration_id,
            }

        aligned = cv2.warpPerspective(
            nir,
            self.homography,
            output_size,
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0),
        )
        return encode_jpeg(aligned), {
            "state": "applied",
            "calibration_id": self.calibration_id,
            "source": self.source_path,
        }
