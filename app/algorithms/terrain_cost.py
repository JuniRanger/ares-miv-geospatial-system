"""Interface for combining validated terrain layers into traversal costs."""

from numpy.typing import NDArray
import numpy as np


def calculate_terrain_cost(
    slope_degrees: NDArray[np.float64] | None,
    roughness: NDArray[np.float64] | None,
) -> NDArray[np.float64]:
    """Calculate traversal costs from aligned, validated terrain measurements."""
    raise NotImplementedError("Terrain cost calculation is not implemented.")
