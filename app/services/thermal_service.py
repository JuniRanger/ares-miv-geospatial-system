"""Interface for reading validated thermal measurements."""


def get_thermal_inertia(latitude: float, longitude: float) -> float | None:
    """Return thermal inertia in source-validated units, or null when unavailable."""
    raise NotImplementedError("Thermal data access is not implemented.")
