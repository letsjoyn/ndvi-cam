from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "FieldScope"
    database_url: str = f"sqlite:///{(PROJECT_ROOT / 'data' / 'fieldscope.db').as_posix()}"
    data_dir: Path = PROJECT_ROOT / "data"
    static_dir: Path = PROJECT_ROOT / "app" / "static"
    storage_backend: str = "local"
    seed_demo: bool = True
    max_upload_mb: int = 80
    device_ingest_key: str = ""
    s3_bucket: str = ""
    s3_region: str = ""
    s3_endpoint_url: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    webcam_enabled: bool = True
    webcam_index: int = 0
    webcam_name: str = "USB RGB camera"
    webcam_width: int = 1280
    webcam_height: int = 720
    webcam_fps: int = 30
    webcam_zoom: float = 1.0

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(os.getenv("DATA_DIR", str(PROJECT_ROOT / "data"))).resolve()
        default_db = f"sqlite:///{(data_dir / 'fieldscope.db').as_posix()}"
        return cls(
            app_name=os.getenv("APP_NAME", "FieldScope"),
            database_url=os.getenv("DATABASE_URL", default_db),
            data_dir=data_dir,
            static_dir=PROJECT_ROOT / "app" / "static",
            storage_backend=os.getenv("STORAGE_BACKEND", "local").strip().lower(),
            seed_demo=_env_bool("SEED_DEMO", True),
            max_upload_mb=int(os.getenv("MAX_UPLOAD_MB", "80")),
            device_ingest_key=os.getenv("DEVICE_INGEST_KEY", ""),
            s3_bucket=os.getenv("S3_BUCKET", ""),
            s3_region=os.getenv("S3_REGION", ""),
            s3_endpoint_url=os.getenv("S3_ENDPOINT_URL", ""),
            s3_access_key_id=os.getenv("S3_ACCESS_KEY_ID", ""),
            s3_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY", ""),
            webcam_enabled=_env_bool("WEBCAM_ENABLED", True),
            webcam_index=int(os.getenv("WEBCAM_INDEX", "0")),
            webcam_name=os.getenv("WEBCAM_NAME", "USB RGB camera"),
            webcam_width=int(os.getenv("WEBCAM_WIDTH", "1280")),
            webcam_height=int(os.getenv("WEBCAM_HEIGHT", "720")),
            webcam_fps=int(os.getenv("WEBCAM_FPS", "30")),
            webcam_zoom=float(os.getenv("WEBCAM_ZOOM", "1.0")),
        )

    @property
    def media_dir(self) -> Path:
        return self.data_dir / "media"
