from __future__ import annotations

import io
from abc import ABC, abstractmethod
from pathlib import Path, PurePosixPath

from .config import Settings


def normalize_key(key: str) -> str:
    normalized = str(PurePosixPath(key.replace("\\", "/")))
    if normalized.startswith("/") or normalized == "." or ".." in PurePosixPath(normalized).parts:
        raise ValueError("Invalid storage key")
    return normalized


class Storage(ABC):
    @abstractmethod
    def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_bytes(self, key: str) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def exists(self, key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> None:
        raise NotImplementedError


class LocalStorage(Storage):
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self.root / normalize_key(key)).resolve()
        if self.root != path and self.root not in path.parents:
            raise ValueError("Storage path escaped the media root")
        return path

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".part")
        temp.write_bytes(data)
        temp.replace(path)

    def get_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()


class S3Storage(Storage):
    def __init__(self, settings: Settings) -> None:
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError as exc:
            raise RuntimeError(
                "S3 storage requires requirements-cloud.txt to be installed"
            ) from exc

        if not settings.s3_bucket:
            raise RuntimeError("S3_BUCKET is required when STORAGE_BACKEND=s3")

        self.bucket = settings.s3_bucket
        self.client_error = ClientError
        self.client = boto3.client(
            "s3",
            region_name=settings.s3_region or None,
            endpoint_url=settings.s3_endpoint_url or None,
            aws_access_key_id=settings.s3_access_key_id or None,
            aws_secret_access_key=settings.s3_secret_access_key or None,
        )

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        self.client.upload_fileobj(
            io.BytesIO(data),
            self.bucket,
            normalize_key(key),
            ExtraArgs={"ContentType": content_type},
        )

    def get_bytes(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=normalize_key(key))
        return response["Body"].read()

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=normalize_key(key))
            return True
        except self.client_error:
            return False

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=normalize_key(key))


def build_storage(settings: Settings) -> Storage:
    if settings.storage_backend == "local":
        return LocalStorage(settings.media_dir)
    if settings.storage_backend == "s3":
        return S3Storage(settings)
    raise RuntimeError(f"Unsupported storage backend: {settings.storage_backend}")
