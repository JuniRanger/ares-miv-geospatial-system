"""Interface for identifying route risks from validated measurements."""

from collections.abc import Mapping


def analyze_risks(measurements: Mapping[str, float | None]) -> list[str]:
    """Return risk warning descriptions without assuming unavailable measurements."""
    raise NotImplementedError("Terrain risk analysis is not implemented.")
