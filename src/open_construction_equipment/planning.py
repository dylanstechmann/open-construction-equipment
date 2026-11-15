# SPDX-License-Identifier: Apache-2.0
"""Visibility-checked occupancy-grid A* with deterministic ties."""

from __future__ import annotations

from dataclasses import dataclass
import heapq
import math

from .geometry import Circle, Point, circle_in_polygon, obstacle_clearance, segment_is_clear


class NoPathError(RuntimeError):
    def __init__(self, reason: str, detail: str):
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class GridPlan:
    path: tuple[Point, ...]
    visited_cells: int
    blocked_cells: int
    resolution_m: float
    inflation_radius_m: float


class OccupancyGrid:
    """A cell is free only if its center footprint is free.

    Center occupancy is only a conservative grid approximation. Every actual
    grid edge and exact endpoint connector is separately checked as a swept
    circle before it can enter a returned path.
    """

    def __init__(self, geofence: tuple[Point, ...], obstacles: tuple[Circle, ...], resolution: float, inflation: float):
        if not math.isfinite(resolution) or resolution <= 0 or not math.isfinite(inflation) or inflation < 0:
            raise ValueError("resolution must be positive and inflation non-negative")
        self.geofence, self.obstacles = geofence, obstacles
        self.resolution, self.inflation = resolution, inflation
        self.min_x = min(p.x for p in geofence)
        self.min_y = min(p.y for p in geofence)
        self.max_x = max(p.x for p in geofence)
        self.max_y = max(p.y for p in geofence)
        self.columns = max(1, math.ceil((self.max_x - self.min_x) / resolution))
        self.rows = max(1, math.ceil((self.max_y - self.min_y) / resolution))
        self.blocked: set[tuple[int, int]] = set()
        for row in range(self.rows):
            for column in range(self.columns):
                if not self.world_free(self.cell_center((column, row))):
                    self.blocked.add((column, row))

    def world_free(self, point: Point) -> bool:
        return circle_in_polygon(point, self.inflation, self.geofence) and obstacle_clearance(point, self.inflation, self.obstacles) >= 0

    def segment_free(self, start: Point, end: Point) -> bool:
        return segment_is_clear(start, end, self.inflation, self.geofence, self.obstacles)

    def world_to_cell(self, point: Point) -> tuple[int, int]:
        return (math.floor((point.x - self.min_x) / self.resolution),
                math.floor((point.y - self.min_y) / self.resolution))

    def cell_center(self, cell: tuple[int, int]) -> Point:
        column, row = cell
        return Point(self.min_x + (column + 0.5) * self.resolution,
                     self.min_y + (row + 0.5) * self.resolution)

    def in_bounds(self, cell: tuple[int, int]) -> bool:
        column, row = cell
        return 0 <= column < self.columns and 0 <= row < self.rows

    def free(self, cell: tuple[int, int]) -> bool:
        return self.in_bounds(cell) and cell not in self.blocked


def _heuristic(a: tuple[int, int], b: tuple[int, int]) -> float:
    dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
    return max(dx, dy) + (math.sqrt(2.0) - 1.0) * min(dx, dy)


def _result_path(grid: OccupancyGrid, points: list[Point], visited: int) -> GridPlan:
    distinct: list[Point] = []
    for point in points:
        if not distinct or point != distinct[-1]:
            distinct.append(point)
    if any(not grid.segment_free(start, end) for start, end in zip(distinct, distinct[1:])):
        raise NoPathError("no_path", "internal visibility check rejected a planned segment")
    return GridPlan(tuple(distinct), visited, len(grid.blocked), grid.resolution, grid.inflation)


def plan_path(geofence: tuple[Point, ...], obstacles: tuple[Circle, ...], start: Point, goal: Point,
              resolution: float, inflation: float) -> GridPlan:
    grid = OccupancyGrid(geofence, obstacles, resolution, inflation)
    if not grid.world_free(start):
        raise NoPathError("start_blocked", "start footprint violates geofence or obstacle clearance")
    if not grid.world_free(goal):
        raise NoPathError("goal_blocked", "goal footprint violates geofence or obstacle clearance")
    if start == goal:
        return GridPlan((start,), 0, len(grid.blocked), resolution, inflation)
    start_cell, goal_cell = grid.world_to_cell(start), grid.world_to_cell(goal)
    if start_cell == goal_cell and grid.segment_free(start, goal):
        return _result_path(grid, [start, goal], 0)

    free_cells = [(column, row) for row in range(grid.rows) for column in range(grid.columns)
                  if grid.free((column, row))]

    def connector_free(endpoint: Point, cell: tuple[int, int]) -> bool:
        origin = grid.world_to_cell(endpoint)
        dx = (cell[0] > origin[0]) - (cell[0] < origin[0])
        dy = (cell[1] > origin[1]) - (cell[1] < origin[1])
        if dx and dy:
            # Endpoint connectors obey the same conservative corner rule as A*.
            if not grid.free((origin[0] + dx, origin[1])) or not grid.free((origin[0], origin[1] + dy)):
                return False
        return grid.segment_free(endpoint, grid.cell_center(cell))

    start_cells = [cell for cell in free_cells if connector_free(start, cell)]
    goal_cells = [cell for cell in free_cells if connector_free(goal, cell)]
    if not start_cells:
        raise NoPathError("no_path", "start has no collision-free connector to a free grid-cell center")
    if not goal_cells:
        raise NoPathError("no_path", "goal has no collision-free connector from a free grid-cell center")
    goal_set = set(goal_cells)

    def heuristic(cell: tuple[int, int]) -> float:
        return min(_heuristic(cell, candidate) + grid.cell_center(candidate).distance(goal) / resolution
                   for candidate in goal_cells)

    # Cardinal moves precede diagonals; heap fields provide stable deterministic ties.
    neighbors = ((1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, 1), (-1, -1), (1, -1))
    frontier: list[tuple[float, float, int, int]] = []
    costs: dict[tuple[int, int], float] = {}
    for cell in start_cells:
        cost = start.distance(grid.cell_center(cell)) / resolution
        costs[cell] = cost
        estimate = heuristic(cell)
        heapq.heappush(frontier, (cost + estimate, estimate, *cell))
    parents: dict[tuple[int, int], tuple[int, int]] = {}
    closed: set[tuple[int, int]] = set()
    while frontier:
        _, _, column, row = heapq.heappop(frontier)
        current = (column, row)
        if current in closed:
            continue
        closed.add(current)
        if current in goal_set:
            cells = [current]
            while current in parents:
                current = parents[current]
                cells.append(current)
            cells.reverse()
            points = [start] + [grid.cell_center(cell) for cell in cells] + [goal]
            return _result_path(grid, points, len(closed))
        for dx, dy in neighbors:
            candidate = (column + dx, row + dy)
            if not grid.free(candidate) or candidate in closed:
                continue
            if dx and dy:
                # Both adjacent cardinal cells must be free: no diagonal corner cutting.
                if not grid.free((column + dx, row)) or not grid.free((column, row + dy)):
                    continue
            # Cell-center occupancy alone is insufficient: check the whole swept edge.
            if not grid.segment_free(grid.cell_center(current), grid.cell_center(candidate)):
                continue
            step = math.sqrt(2.0) if dx and dy else 1.0
            new_cost = costs[current] + step
            if new_cost + 1e-12 < costs.get(candidate, math.inf):
                costs[candidate] = new_cost
                parents[candidate] = current
                estimate = heuristic(candidate)
                heapq.heappush(frontier, (new_cost + estimate, estimate, candidate[0], candidate[1]))
    raise NoPathError("no_path", f"no visibility-checked route after visiting {len(closed)} free cells")
