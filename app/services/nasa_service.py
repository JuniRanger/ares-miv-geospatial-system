"""Interfaces for discovery and ingestion of validated NASA data products."""

from app.schemas.common import LayerMetadata


def list_layers() -> list[LayerMetadata]:
    """Return metadata only for datasets that have been downloaded and validated."""
    raise NotImplementedError("NASA dataset discovery is not implemented.")


def ingest_dataset(source: str) -> None:
    """Download and validate a configured source outside normal API requests."""
    raise NotImplementedError("NASA dataset ingestion is not implemented.")
