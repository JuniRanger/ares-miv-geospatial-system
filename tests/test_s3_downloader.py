"""Tests for downloading and caching the route planner's slope raster."""

import base64
import hashlib
from io import BytesIO

import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.config import settings
from app.storage import s3_downloader
from app.storage.s3_downloader import ensure_slope_raster
from app.storage.slope_raster import is_valid_slope_raster

MARS_EQC = (
    "+proj=eqc +lat_ts=0 +lat_0=0 +lon_0=0 "
    "+a=3396190 +b=3396190 +units=m +no_defs"
)


def _raster_bytes(tmp_path) -> bytes:
    path = tmp_path / "source.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=8,
        height=6,
        count=1,
        dtype="float32",
        crs=MARS_EQC,
        transform=from_origin(100.0, 200.0, 5.0, 5.0),
        nodata=-9999.0,
    ) as dataset:
        dataset.write(np.zeros((6, 8), dtype=np.float32), 1)
    return path.read_bytes()


class FakeS3Client:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.get_calls = 0

    def head_object(self, **request):
        assert request["ChecksumMode"] == "ENABLED"
        checksum = base64.b64encode(hashlib.sha256(self.content).digest()).decode("ascii")
        return {
            "ContentLength": len(self.content),
            "ETag": '"slope-version-1"',
            "VersionId": "version-1",
            "ChecksumSHA256": checksum,
            "ChecksumType": "FULL_OBJECT",
        }

    def get_object(self, **_request):
        self.get_calls += 1
        return {"Body": BytesIO(self.content), "ContentLength": len(self.content)}


def _configure_cache(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "ruta_pendiente", tmp_path / "cache" / "slope_5m.tif")
    monkeypatch.setattr(settings, "s3_bucket", "mars-terrain-data-2026")
    monkeypatch.setattr(settings, "s3_key", "slope_5m.tif")
    monkeypatch.setattr(settings, "s3_region", "us-east-2")
    monkeypatch.setattr(settings, "s3_version_id", None)
    monkeypatch.setattr(settings, "s3_sha256", None)


def test_downloaded_raster_is_validated_and_reused_from_manifest(
    tmp_path, monkeypatch
) -> None:
    content = _raster_bytes(tmp_path)
    client = FakeS3Client(content)
    _configure_cache(tmp_path, monkeypatch)
    monkeypatch.setattr(s3_downloader, "_create_s3_client", lambda: client)

    downloaded = ensure_slope_raster()
    cached = ensure_slope_raster()

    assert downloaded.status == "downloaded"
    assert downloaded.available
    assert is_valid_slope_raster(downloaded.path)
    assert cached.status == "cached"
    assert cached.available
    assert client.get_calls == 1
    manifest = downloaded.manifest_path.read_text(encoding="utf-8")
    assert '"bounds": [' in manifest
    assert '"transform": [' in manifest


def test_failed_download_preserves_a_valid_local_copy(tmp_path, monkeypatch) -> None:
    content = _raster_bytes(tmp_path)
    _configure_cache(tmp_path, monkeypatch)
    target_path = settings.ruta_pendiente
    target_path.parent.mkdir(parents=True)
    target_path.write_bytes(content)
    client = FakeS3Client(b"not-a-raster")
    monkeypatch.setattr(s3_downloader, "_create_s3_client", lambda: client)
    monkeypatch.setattr(settings, "s3_sha256", "0" * 64)

    result = ensure_slope_raster()

    assert result.status == "stale_cache"
    assert result.available
    assert target_path.read_bytes() == content
    assert is_valid_slope_raster(target_path)
