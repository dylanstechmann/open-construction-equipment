# SPDX-License-Identifier: Apache-2.0
"""Deterministic planar geometry in SI units (metres and radians)."""

from __future__ import annotations

from dataclasses import dataclass
import math

from .models import Pose

EPSILON = 1e-9


@dataclass(frozen=True, order=True)
class Point:
    x: float
    y: float

    def distance(self, other: "Point") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def as_pose(self, yaw: float = 0.0) -> Pose:
        return Pose(self.x, self.y, yaw)


@dataclass(frozen=True)
class Circle:
    center: Point
    radius: float


def wrap_angle(angle: float) -> float:
    """Wrap a finite angle to [-pi, pi)."""
    if not math.isfinite(angle):
        raise ValueError("angle must be finite")
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def point_segment_distance(point: Point, start: Point, end: Point) -> float:
    dx, dy = end.x - start.x, end.y - start.y
    length_sq = dx * dx + dy * dy
    if length_sq <= EPSILON:
        return point.distance(start)
    fraction = clamp(((point.x - start.x) * dx + (point.y - start.y) * dy) / length_sq, 0.0, 1.0)
    projection = Point(start.x + fraction * dx, start.y + fraction * dy)
    return point.distance(projection)


def _orientation(a: Point, b: Point, c: Point) -> float:
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)


def _on_segment(a: Point, b: Point, p: Point) -> bool:
    return (
        abs(_orientation(a, b, p)) <= EPSILON
        and min(a.x, b.x) - EPSILON <= p.x <= max(a.x, b.x) + EPSILON
        and min(a.y, b.y) - EPSILON <= p.y <= max(a.y, b.y) + EPSILON
    )


def segments_intersect(a: Point, b: Point, c: Point, d: Point) -> bool:
    """Include endpoint contact and collinear overlap as intersections."""
    ab_c, ab_d = _orientation(a, b, c), _orientation(a, b, d)
    cd_a, cd_b = _orientation(c, d, a), _orientation(c, d, b)
    if ((ab_c > EPSILON and ab_d < -EPSILON) or (ab_c < -EPSILON and ab_d > EPSILON)) and (
        (cd_a > EPSILON and cd_b < -EPSILON) or (cd_a < -EPSILON and cd_b > EPSILON)
    ):
        return True
    return any((
        abs(ab_c) <= EPSILON and _on_segment(a, b, c),
        abs(ab_d) <= EPSILON and _on_segment(a, b, d),
        abs(cd_a) <= EPSILON and _on_segment(c, d, a),
        abs(cd_b) <= EPSILON and _on_segment(c, d, b),
    ))


def point_in_polygon(point: Point, polygon: tuple[Point, ...] | list[Point]) -> bool:
    """Ray casting with boundary points treated as inside."""
    if len(polygon) < 3:
        return False
    inside = False
    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]
        if point_segment_distance(point, start, end) <= EPSILON:
            return True
        crosses = (start.y > point.y) != (end.y > point.y)
        if crosses:
            crossing_x = start.x + (point.y - start.y) * (end.x - start.x) / (end.y - start.y)
            if point.x < crossing_x:
                inside = not inside
    return inside


def polygon_edge_distance(point: Point, polygon: tuple[Point, ...] | list[Point]) -> float:
    if len(polygon) < 3:
        return math.inf
    return min(
        point_segment_distance(point, start, polygon[(index + 1) % len(polygon)])
        for index, start in enumerate(polygon)
    )


def circle_in_polygon(center: Point, radius: float, polygon: tuple[Point, ...]) -> bool:
    """Conservative circular-footprint containment, including the boundary."""
    return point_in_polygon(center, polygon) and polygon_edge_distance(center, polygon) + EPSILON >= radius


def is_simple_polygon(polygon: tuple[Point, ...] | list[Point]) -> bool:
    """Return whether a closed ring has no self-contact or zero-length edges.

    Adjacent edges may share their one ring vertex. Every non-adjacent contact,
    including endpoint touching and collinear overlap, is an intersection.
    """
    if len(polygon) < 3:
        return False
    edges = [(start, polygon[(index + 1) % len(polygon)]) for index, start in enumerate(polygon)]
    if any(start.distance(end) <= EPSILON for start, end in edges):
        return False
    for first, (a, b) in enumerate(edges):
        for second in range(first + 1, len(edges)):
            if second == first + 1 or (first == 0 and second == len(edges) - 1):
                continue
            c, d = edges[second]
            if segments_intersect(a, b, c, d):
                return False
    return True


def segment_segment_distance(a: Point, b: Point, c: Point, d: Point) -> float:
    """Exact minimum distance between two closed line segments."""
    if segments_intersect(a, b, c, d):
        return 0.0
    return min(point_segment_distance(c, a, b), point_segment_distance(d, a, b),
               point_segment_distance(a, c, d), point_segment_distance(b, c, d))


def _segment_polygon_intervals(start: Point, end: Point, polygon: tuple[Point, ...]) -> list[float]:
    """Return path fractions at which polygon containment can change."""
    dx, dy = end.x - start.x, end.y - start.y
    fractions = [0.0, 1.0]
    for index, edge_start in enumerate(polygon):
        edge_end = polygon[(index + 1) % len(polygon)]
        if not segments_intersect(start, end, edge_start, edge_end):
            continue
        ex, ey = edge_end.x - edge_start.x, edge_end.y - edge_start.y
        denominator = dx * ey - dy * ex
        if denominator != 0.0:
            fraction = ((edge_start.x - start.x) * ey - (edge_start.y - start.y) * ex) / denominator
            fractions.append(clamp(fraction, 0.0, 1.0))
        else:
            # Collinear contact: both edge endpoints delimit containment intervals.
            length_sq = dx * dx + dy * dy
            if length_sq > EPSILON:
                for point in (edge_start, edge_end):
                    fraction = ((point.x - start.x) * dx + (point.y - start.y) * dy) / length_sq
                    fractions.append(clamp(fraction, 0.0, 1.0))
    return sorted(set(fractions))


def segment_in_polygon(start: Point, end: Point, polygon: tuple[Point, ...]) -> bool:
    """Check the entire segment, including excursions through concave boundaries."""
    if start.distance(end) <= EPSILON:
        return point_in_polygon(start, polygon)
    fractions = _segment_polygon_intervals(start, end, polygon)
    if not point_in_polygon(start, polygon) or not point_in_polygon(end, polygon):
        return False
    for left, right in zip(fractions, fractions[1:]):
        if right - left <= EPSILON:
            continue
        fraction = (left + right) / 2.0
        midpoint = Point(start.x + fraction * (end.x - start.x), start.y + fraction * (end.y - start.y))
        if not point_in_polygon(midpoint, polygon):
            return False
    return True


def segment_is_clear(start: Point, end: Point, footprint_radius: float,
                     geofence: tuple[Point, ...], obstacles: tuple[Circle, ...] = ()) -> bool:
    """Check a swept circular footprint over a complete continuous segment.

    Boundary distances are evaluated between segments, not just at cell centers
    or endpoints. This covers exact endpoint connectors and concave fences.
    """
    if not segment_in_polygon(start, end, geofence):
        return False
    for index, edge_start in enumerate(geofence):
        edge_end = geofence[(index + 1) % len(geofence)]
        if segment_segment_distance(start, end, edge_start, edge_end) + EPSILON < footprint_radius:
            return False
    return all(point_segment_distance(obstacle.center, start, end) + EPSILON >= footprint_radius + obstacle.radius
               for obstacle in obstacles)


def obstacle_clearance(center: Point, footprint_radius: float, obstacles: tuple[Circle, ...]) -> float:
    """Signed minimum surface clearance; negative means footprint overlap."""
    if not obstacles:
        return math.inf
    return min(center.distance(item.center) - footprint_radius - item.radius for item in obstacles)


def path_length(path: list[Point] | tuple[Point, ...]) -> float:
    return sum(start.distance(end) for start, end in zip(path, path[1:]))
