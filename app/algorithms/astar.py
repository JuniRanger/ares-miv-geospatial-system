"""Búsqueda A* sobre una ventana ráster ponderada."""

from heapq import heappop, heappush
from itertools import count

from numpy.typing import NDArray
import numpy as np

from app.config import MAX_EXPANSIONES


class ExpansionLimitExceeded(RuntimeError):
    """Se lanza cuando A* supera el límite de expansiones configurado."""


def find_path(
    cost_grid: NDArray[np.float64],
    start: tuple[int, int],
    goal: tuple[int, int],
    cell_size_x_m: float = 5.0,
    cell_size_y_m: float = 5.0,
    max_expansions: int | None = None,
) -> list[tuple[int, int]] | None:
    """Encontrar la ruta mínima con ocho vecinos; infinito significa impasable."""
    height, width = cost_grid.shape
    if not (0 <= start[0] < height and 0 <= start[1] < width):
        return None
    if not (0 <= goal[0] < height and 0 <= goal[1] < width):
        return None
    if not np.isfinite(cost_grid[start]) or not np.isfinite(cost_grid[goal]):
        return None

    expansion_limit = MAX_EXPANSIONES if max_expansions is None else max_expansions
    sequence = count()
    frontier: list[tuple[float, int, tuple[int, int]]] = []
    heappush(frontier, (_heuristic(start, goal, cell_size_x_m, cell_size_y_m), next(sequence), start))
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    costs: dict[tuple[int, int], float] = {start: 0.0}
    closed: set[tuple[int, int]] = set()
    expanded = 0
    directions = (
        (-1, 0),
        (0, -1),
        (0, 1),
        (1, 0),
        (-1, -1),
        (-1, 1),
        (1, -1),
        (1, 1),
    )

    while frontier:
        _, _, current = heappop(frontier)
        if current in closed:
            continue
        if current == goal:
            return _reconstruct_path(came_from, current)
        if expanded >= expansion_limit:
            raise ExpansionLimitExceeded
        expanded += 1
        closed.add(current)

        for row_offset, col_offset in directions:
            neighbor = current[0] + row_offset, current[1] + col_offset
            row, col = neighbor
            if not (0 <= row < height and 0 <= col < width):
                continue
            if neighbor in closed or not np.isfinite(cost_grid[neighbor]):
                continue
            if row_offset and col_offset:
                if (
                    not np.isfinite(cost_grid[current[0] + row_offset, current[1]])
                    or not np.isfinite(cost_grid[current[0], current[1] + col_offset])
                ):
                    continue

            step_distance = float(
                np.hypot(col_offset * cell_size_x_m, row_offset * cell_size_y_m)
            )
            step_cost = step_distance * (cost_grid[current] + cost_grid[neighbor]) / 2.0
            candidate_cost = costs[current] + float(step_cost)
            if candidate_cost >= costs.get(neighbor, float("inf")):
                continue

            came_from[neighbor] = current
            costs[neighbor] = candidate_cost
            estimate = candidate_cost + _heuristic(
                neighbor, goal, cell_size_x_m, cell_size_y_m
            )
            heappush(frontier, (estimate, next(sequence), neighbor))

    return None


def _heuristic(
    current: tuple[int, int],
    goal: tuple[int, int],
    cell_size_x_m: float,
    cell_size_y_m: float,
) -> float:
    """Usar distancia recta como cota inferior del costo ponderado."""
    return float(
        np.hypot(
            (goal[1] - current[1]) * cell_size_x_m,
            (goal[0] - current[0]) * cell_size_y_m,
        )
    )


def _reconstruct_path(
    came_from: dict[tuple[int, int], tuple[int, int]],
    current: tuple[int, int],
) -> list[tuple[int, int]]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path
