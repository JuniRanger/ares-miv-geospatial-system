"""Download and atomically cache the route planner's slope GeoTIFF from S3."""

import base64
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Literal

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from app.config import settings
from app.storage.slope_raster import (
    SlopeRasterMetadata,
    SlopeRasterValidationError,
    inspect_slope_raster,
)

logger = logging.getLogger(__name__)
_CHUNK_SIZE = 8 * 1024 * 1024
_SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass(frozen=True)
class DatasetPreparationResult:
    """Outcome of checking or refreshing the local slope raster cache."""

    status: Literal["cached", "downloaded", "stale_cache", "unavailable"]
    available: bool
    path: Path
    message: str
    error_code: str | None = None
    manifest_path: Path | None = None


def ensure_slope_raster(force: bool = False) -> DatasetPreparationResult:
    """Validate or download the configured object without raising into FastAPI."""
    target_path = Path(settings.ruta_pendiente)
    manifest_path = _manifest_path(target_path)

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with _destination_lock(target_path):
            return _ensure_locked(target_path, manifest_path, force)
    except Exception as error:
        error_code = _safe_error_code(error)
        logger.error("No se pudo preparar el raster de pendiente (%s).", error_code)
        if _is_valid_local_file(target_path):
            return _result(
                "stale_cache",
                True,
                target_path,
                "Se conserva la copia local válida; no se pudo actualizar desde S3.",
                error_code,
                manifest_path,
            )
        return _result(
            "unavailable",
            False,
            target_path,
            "No hay un raster local válido y la preparación desde S3 falló.",
            error_code,
            manifest_path,
        )


def _ensure_locked(
    target_path: Path,
    manifest_path: Path,
    force: bool,
) -> DatasetPreparationResult:
    """Run the S3 check and possible download while holding the file lock."""
    local_metadata = _local_metadata(target_path)
    local_manifest = _verified_manifest(target_path, manifest_path, local_metadata)

    if not settings.s3_bucket.strip() or not settings.s3_key.strip():
        return _local_or_unavailable(
            target_path,
            manifest_path,
            "Falta configurar S3_BUCKET o S3_KEY.",
            "S3_CONFIGURATION_MISSING",
        )

    try:
        client = _create_s3_client()
        request = _object_request()
        remote = client.head_object(**request, ChecksumMode="ENABLED")
    except Exception as error:
        error_code = _safe_error_code(error)
        logger.warning("No se pudo consultar el objeto de pendiente en S3 (%s).", error_code)
        return _local_or_unavailable(
            target_path,
            manifest_path,
            "No se pudo consultar S3; se conserva cualquier copia local válida.",
            error_code,
        )

    if (
        not force
        and local_metadata is not None
        and local_manifest is not None
        and _same_remote_object(local_manifest, remote)
        and _matches_expected_sha256(local_manifest.get("sha256"))
    ):
        return _result(
            "cached",
            True,
            target_path,
            "La copia local válida corresponde al objeto S3 configurado.",
            None,
            manifest_path,
        )

    temporary_path: Path | None = None
    try:
        temporary_path = _create_temporary_file(target_path)
        downloaded_size, downloaded_sha256 = _download_object(
            client, request, remote, temporary_path
        )
        expected_size = remote.get("ContentLength")
        if not isinstance(expected_size, int) or expected_size <= 0:
            raise DownloadValidationError(
                "S3_OBJECT_SIZE_INVALID", "S3 no reportó un tamaño válido."
            )
        if downloaded_size != expected_size:
            raise DownloadValidationError(
                "S3_SIZE_MISMATCH", "El tamaño descargado no coincide con ContentLength."
            )
        _verify_expected_sha256(downloaded_sha256)
        _verify_s3_checksum(downloaded_sha256, remote)
        raster_metadata = inspect_slope_raster(temporary_path)
        _publish(
            temporary_path,
            target_path,
            manifest_path,
            _build_manifest(
                remote,
                downloaded_size,
                downloaded_sha256,
                raster_metadata,
            ),
        )
        temporary_path = None
        return _result(
            "downloaded",
            True,
            target_path,
            "El GeoTIFF se descargó, validó y publicó en la caché local.",
            None,
            manifest_path,
        )
    except Exception as error:
        error_code = _safe_error_code(error)
        logger.error("No se pudo validar o publicar el raster descargado (%s).", error_code)
        return _local_or_unavailable(
            target_path,
            manifest_path,
            "La nueva descarga no se publicó; se conserva la copia local válida, si existe.",
            error_code,
        )
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


class DownloadValidationError(ValueError):
    """An S3 object failed size or checksum validation."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _create_s3_client():
    """Create an S3 client using explicit environment credentials or boto3's chain."""
    access_key = _secret_value(settings.aws_access_key_id)
    secret_key = _secret_value(settings.aws_secret_access_key)
    if bool(access_key) != bool(secret_key):
        raise DownloadValidationError(
            "AWS_CREDENTIALS_INCOMPLETE",
            "AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY deben configurarse juntos.",
        )

    client_options: dict[str, object] = {
        "region_name": settings.s3_region.strip() or settings.aws_default_region,
        "endpoint_url": settings.s3_endpoint_url or None,
        "config": Config(
            connect_timeout=3,
            read_timeout=30,
            retries={"max_attempts": 2, "mode": "standard"},
        ),
    }
    if access_key and secret_key:
        client_options["aws_access_key_id"] = access_key
        client_options["aws_secret_access_key"] = secret_key
    return boto3.client("s3", **client_options)


def _secret_value(value) -> str | None:
    if value is None:
        return None
    secret = value.get_secret_value().strip()
    return secret or None


def _object_request() -> dict[str, str]:
    request = {"Bucket": settings.s3_bucket.strip(), "Key": settings.s3_key.strip()}
    version_id = (settings.s3_version_id or "").strip()
    if version_id:
        request["VersionId"] = version_id
    return request


def _download_object(
    client,
    request: dict[str, str],
    remote: dict[str, object],
    temporary_path: Path,
) -> tuple[int, str]:
    response = client.get_object(**request)
    body = response["Body"]
    digest = hashlib.sha256()
    size = 0
    try:
        with temporary_path.open("wb") as output:
            while chunk := body.read(_CHUNK_SIZE):
                output.write(chunk)
                digest.update(chunk)
                size += len(chunk)
            output.flush()
            os.fsync(output.fileno())
    finally:
        body.close()

    response_size = response.get("ContentLength")
    if response_size is not None and response_size != size:
        raise DownloadValidationError(
            "S3_RESPONSE_SIZE_MISMATCH",
            "El tamaño leído no coincide con el tamaño de la respuesta S3.",
        )
    if remote.get("ContentLength") != size:
        raise DownloadValidationError(
            "S3_SIZE_MISMATCH", "El tamaño descargado no coincide con ContentLength."
        )
    return size, digest.hexdigest()


def _verify_expected_sha256(actual_sha256: str) -> None:
    expected = (settings.s3_sha256 or "").strip().lower()
    if not expected:
        return
    if not _SHA256_PATTERN.fullmatch(expected):
        raise DownloadValidationError(
            "S3_SHA256_INVALID", "S3_SHA256 debe contener 64 caracteres hexadecimales."
        )
    if actual_sha256 != expected:
        raise DownloadValidationError(
            "S3_SHA256_MISMATCH", "El SHA-256 descargado no coincide con S3_SHA256."
        )


def _verify_s3_checksum(actual_sha256: str, remote: dict[str, object]) -> None:
    checksum = remote.get("ChecksumSHA256")
    checksum_type = remote.get("ChecksumType")
    if checksum and checksum_type == "FULL_OBJECT":
        actual_base64 = base64.b64encode(bytes.fromhex(actual_sha256)).decode("ascii")
        if actual_base64 != checksum:
            raise DownloadValidationError(
                "S3_CHECKSUM_MISMATCH",
                "El SHA-256 de la descarga no coincide con el checksum FULL_OBJECT de S3.",
            )


def _build_manifest(
    remote: dict[str, object],
    size: int,
    sha256: str,
    raster_metadata: SlopeRasterMetadata,
) -> dict[str, object]:
    return {
        "bucket": settings.s3_bucket.strip(),
        "key": settings.s3_key.strip(),
        "version_id": remote.get("VersionId"),
        "etag": remote.get("ETag"),
        "s3_checksum_sha256": remote.get("ChecksumSHA256"),
        "sha256": sha256,
        "size_bytes": size,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "raster": raster_metadata.as_dict(),
    }


def _manifest_path(target_path: Path) -> Path:
    return target_path.with_name(f"{target_path.stem}.manifest.json")


def _create_temporary_file(target_path: Path) -> Path:
    with tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=f".{target_path.name}.",
        suffix=".part",
        dir=target_path.parent,
        delete=False,
    ) as temporary:
        return Path(temporary.name)


def _publish(
    temporary_path: Path,
    target_path: Path,
    manifest_path: Path,
    manifest: dict[str, object],
) -> None:
    manifest_temporary = _create_temporary_file(manifest_path)
    try:
        with manifest_temporary.open("w", encoding="utf-8") as output:
            json.dump(manifest, output, ensure_ascii=False, indent=2, allow_nan=False)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary_path, target_path)
        os.replace(manifest_temporary, manifest_path)
    finally:
        manifest_temporary.unlink(missing_ok=True)


def _local_metadata(path: Path) -> SlopeRasterMetadata | None:
    if not path.is_file():
        return None
    try:
        return inspect_slope_raster(path)
    except SlopeRasterValidationError:
        return None


def _verified_manifest(
    target_path: Path,
    manifest_path: Path,
    raster_metadata: SlopeRasterMetadata | None,
) -> dict[str, object] | None:
    if raster_metadata is None or not manifest_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            return None
        if manifest.get("size_bytes") != target_path.stat().st_size:
            return None
        if manifest.get("raster") != raster_metadata.as_dict():
            return None
        if manifest.get("sha256") != _sha256_file(target_path):
            return None
        return manifest
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def _same_remote_object(
    manifest: dict[str, object],
    remote: dict[str, object],
) -> bool:
    if manifest.get("bucket") != settings.s3_bucket or manifest.get("key") != settings.s3_key:
        return False
    remote_version = remote.get("VersionId")
    local_version = manifest.get("version_id")
    if remote_version or local_version:
        return remote_version == local_version
    remote_etag = remote.get("ETag")
    return bool(remote_etag) and remote_etag == manifest.get("etag")


def _matches_expected_sha256(local_sha256: object) -> bool:
    expected = (settings.s3_sha256 or "").strip().lower()
    if not expected:
        return True
    return bool(_SHA256_PATTERN.fullmatch(expected)) and local_sha256 == expected


def _local_or_unavailable(
    target_path: Path,
    manifest_path: Path,
    message: str,
    error_code: str,
) -> DatasetPreparationResult:
    if _is_valid_local_file(target_path):
        return _result(
            "stale_cache",
            True,
            target_path,
            message,
            error_code,
            manifest_path,
        )
    return _result(
        "unavailable",
        False,
        target_path,
        message,
        error_code,
        manifest_path,
    )


def _is_valid_local_file(path: Path) -> bool:
    return _local_metadata(path) is not None


def _result(
    status: Literal["cached", "downloaded", "stale_cache", "unavailable"],
    available: bool,
    path: Path,
    message: str,
    error_code: str | None,
    manifest_path: Path,
) -> DatasetPreparationResult:
    return DatasetPreparationResult(
        status=status,
        available=available,
        path=path,
        message=message,
        error_code=error_code,
        manifest_path=manifest_path,
    )


def _safe_error_code(error: Exception) -> str:
    if isinstance(error, DownloadValidationError):
        return error.code
    if isinstance(error, NoCredentialsError):
        return "AWS_CREDENTIALS_UNAVAILABLE"
    if isinstance(error, ClientError):
        return str(error.response.get("Error", {}).get("Code", "S3_CLIENT_ERROR"))
    if isinstance(error, BotoCoreError):
        return "S3_CONNECTION_ERROR"
    if isinstance(error, SlopeRasterValidationError):
        return "INVALID_SLOPE_RASTER"
    return type(error).__name__.upper()


@contextmanager
def _destination_lock(target_path: Path):
    """Serialize refreshes across threads and processes on the Render instance."""
    lock_path = target_path.with_name(f"{target_path.name}.lock")
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)
