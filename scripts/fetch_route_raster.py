"""Descargar o verificar manualmente el GeoTIFF de pendiente desde S3."""

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.storage.s3_downloader import ensure_slope_raster


def main() -> int:
    """Run the same cache refresh used by the FastAPI lifespan."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Descargar de nuevo aunque la caché coincida con el objeto remoto.",
    )
    arguments = parser.parse_args()

    result = ensure_slope_raster(force=arguments.force)
    print(f"{result.status}: {result.message}")
    print(f"Raster local: {result.path}")
    if result.manifest_path is not None:
        print(f"Manifiesto: {result.manifest_path}")
    return 0 if result.available else 1


if __name__ == "__main__":
    raise SystemExit(main())
