from __future__ import annotations

from typing import Protocol

import boto3
from botocore.config import Config

from app.core.config import Settings


class StorageConfigurationError(RuntimeError):
    pass


class ObjectStorage(Protocol):
    def put_object(
        self,
        *,
        key: str,
        body: bytes,
        content_type: str,
    ) -> None: ...

    def presigned_get_url(self, key: str, *, expires_in: int = 3600) -> str | None: ...


class S3ObjectStorage:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = None

    @property
    def _bucket(self) -> str:
        if not self._settings.s3_bucket:
            raise StorageConfigurationError("S3_BUCKET is not configured")
        return self._settings.s3_bucket

    def _get_client(self):
        if self._client is not None:
            return self._client

        if not self._settings.s3_access_key_id or not self._settings.s3_secret_access_key:
            raise StorageConfigurationError("S3 credentials are not configured")

        client_kwargs = {
            "aws_access_key_id": self._settings.s3_access_key_id,
            "aws_secret_access_key": self._settings.s3_secret_access_key,
            "region_name": self._settings.s3_region,
            "config": Config(
                s3={"addressing_style": "path" if self._settings.s3_force_path_style else "auto"}
            ),
        }
        if self._settings.s3_endpoint_url:
            client_kwargs["endpoint_url"] = self._settings.s3_endpoint_url

        self._client = boto3.client("s3", **client_kwargs)
        return self._client

    def put_object(
        self,
        *,
        key: str,
        body: bytes,
        content_type: str,
    ) -> None:
        self._get_client().put_object(
            Bucket=self._bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
        )

    def presigned_get_url(self, key: str, *, expires_in: int = 3600) -> str | None:
        try:
            return self._get_client().generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        except StorageConfigurationError:
            return None
