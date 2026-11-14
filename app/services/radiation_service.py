"""Interface for reading validated radiation measurements."""


def get_radiation(latitude: float, longitude: float) -> float | None:
    """Return a radiation measurement only when a validated source is configured."""
    raise NotImplementedError("Radiation data access is not implemented.")
