"""File storage abstraction: local disk in development, Huawei Cloud OBS in production.

Files are always served back through the authenticated API (never via public
bucket URLs), so the OBS bucket can stay private.
"""

from pathlib import Path
from typing import Protocol

from app.core.config import get_settings


class StorageError(RuntimeError):
    pass


class FileStorage(Protocol):
    name: str

    def put(self, key: str, data: bytes, content_type: str) -> None: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...
    def ping(self) -> bool: ...


class LocalStorage:
    name = "local"

    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root not in path.parents:
            raise StorageError("invalid storage key")
        return path

    def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        path = self._path(key)
        if not path.exists():
            raise StorageError("file not found")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def ping(self) -> bool:
        return self.root.exists()


class OBSStorage:
    """Huawei Cloud OBS through its S3-compatible API."""

    name = "obs"

    def __init__(self, endpoint: str, bucket: str, ak: str, sk: str, region: str) -> None:
        import boto3
        from botocore.config import Config

        self.bucket = bucket
        self._s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=ak,
            aws_secret_access_key=sk,
            region_name=region or None,
            config=Config(s3={"addressing_style": "virtual"}, signature_version="s3v4"),
        )

    def put(self, key: str, data: bytes, content_type: str) -> None:
        try:
            self._s3.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)
        except Exception as exc:
            raise StorageError("could not store file") from exc

    def get(self, key: str) -> bytes:
        try:
            return self._s3.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except Exception as exc:
            raise StorageError("could not read file") from exc

    def delete(self, key: str) -> None:
        try:
            self._s3.delete_object(Bucket=self.bucket, Key=key)
        except Exception as exc:
            raise StorageError("could not delete file") from exc

    def ping(self) -> bool:
        try:
            self._s3.head_bucket(Bucket=self.bucket)
            return True
        except Exception:
            return False


_storage: FileStorage | None = None


def get_storage() -> FileStorage:
    global _storage
    if _storage is None:
        s = get_settings()
        if s.storage_backend == "obs":
            _storage = OBSStorage(
                s.obs_endpoint, s.obs_bucket, s.obs_access_key_id, s.obs_secret_access_key, s.obs_region
            )
        else:
            _storage = LocalStorage(s.local_storage_dir)
    return _storage


def set_storage(storage: FileStorage | None) -> None:
    global _storage
    _storage = storage
