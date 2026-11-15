"""Interface for grid-based A* pathfinding."""

from numpy.typing import NDArray
import numpy as np


def find_path(
    cost_grid: NDArray[np.float64],
    start: tuple[int, int],
    goal: tuple[int, int],
) -> list[tuple[int, int]]:
    """Find a path through a prepared cost grid from start to goal cells."""
    raise NotImplementedError("A* pathfinding is not implemented.")
