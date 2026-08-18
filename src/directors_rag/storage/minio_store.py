"""MinIO-backed immutable storage for raw source documents."""

from __future__ import annotations

import io

from minio import Minio


class MinioDocumentStore:
    """Store and retrieve raw documents in an S3-compatible MinIO bucket."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        *,
        secure: bool = False,
    ) -> None:
        self._client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        self._bucket = bucket

    def ensure_bucket(self) -> None:
        """Create the configured bucket when it does not yet exist."""
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def put_bytes(self, object_key: str, content: bytes, content_type: str) -> None:
        """Upload bytes under a deterministic object key."""
        self.ensure_bucket()
        self._client.put_object(
            self._bucket,
            object_key,
            io.BytesIO(content),
            length=len(content),
            content_type=content_type,
        )

    def get_bytes(self, object_key: str) -> bytes:
        """Read an object and always release the underlying HTTP connection."""
        response = self._client.get_object(self._bucket, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def is_ready(self) -> bool:
        """Return whether the object store is reachable and initialized."""
        try:
            self.ensure_bucket()
        except Exception:  # readiness must collapse vendor-specific errors
            return False
        return True
