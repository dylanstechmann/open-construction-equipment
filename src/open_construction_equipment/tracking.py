# SPDX-License-Identifier: Apache-2.0
"""Bounded pure-pursuit tracking for synthetic skid-steer paths."""

from __future__ import annotations

from dataclasses import dataclass
import math

from .config import LimitConfig, TrackerConfig
from .geometry import Point, clamp, path_length, point_segment_distance, wrap_angle
from .models import Command, Pose

_SHARP_CORNER_ANGLE_RAD = math.pi / 6.0
_CORNER_ADVANCE_LOOKAHEAD_FRACTION = 0.25
_ALIGNMENT_THRESHOLD_RAD = math.pi / 3.0


@dataclass(frozen=True)
class TrackingResult:
    command: Command
    goal_reached: bool
    target: Point
    curvature_inv_m: float
    closest_distance_m: float


class PurePursuitTracker:
    def __init__(self, config: TrackerConfig, limits: LimitConfig):
        self.config, self.limits = config, limits

    def update(self, pose: Pose, path: tuple[Point, ...] | list[Point]) -> TrackingResult:
        if not path:
            raise ValueError("path needs at least one point")
        position = Point(pose.x, pose.y)
        goal = path[-1]
        goal_distance = position.distance(goal)
        if goal_distance <= self.config.goal_tolerance_m:
            return TrackingResult(Command(), True, goal, 0.0, goal_distance)
        if len(path) < 2:
            raise ValueError("a one-point path is valid only when the goal is already reached")
        best_distance, best_segment, best_fraction = math.inf, 0, 0.0
        for index, (start, end) in enumerate(zip(path, path[1:])):
            distance = point_segment_distance(position, start, end)
            if distance < best_distance - 1e-12:
                dx, dy = end.x - start.x, end.y - start.y
                length_sq = dx * dx + dy * dy
                fraction = 0.0 if length_sq == 0 else clamp(((position.x - start.x) * dx + (position.y - start.y) * dy) / length_sq, 0.0, 1.0)
                best_distance, best_segment, best_fraction = distance, index, fraction
        target = goal
        projection = Point(path[best_segment].x + best_fraction * (path[best_segment + 1].x - path[best_segment].x),
                           path[best_segment].y + best_fraction * (path[best_segment + 1].y - path[best_segment].y))
        vertex = path[best_segment + 1]
        vertex_distance = projection.distance(vertex)
        corner_angle = 0.0
        if best_segment + 2 < len(path):
            following = path[best_segment + 2]
            incoming = (vertex.x - path[best_segment].x, vertex.y - path[best_segment].y)
            outgoing = (following.x - vertex.x, following.y - vertex.y)
            incoming_length, outgoing_length = math.hypot(*incoming), math.hypot(*outgoing)
            if incoming_length > 1e-12 and outgoing_length > 1e-12:
                cosine = clamp((incoming[0] * outgoing[0] + incoming[1] * outgoing[1]) /
                               (incoming_length * outgoing_length), -1.0, 1.0)
                corner_angle = math.acos(cosine)
        sharp_corner = corner_angle > _SHARP_CORNER_ANGLE_RAD
        corner_advance_distance = min(self.config.lookahead_m * _CORNER_ADVANCE_LOOKAHEAD_FRACTION,
                                               self.config.goal_tolerance_m)
        lookahead = self.config.lookahead_m
        if sharp_corner and vertex_distance > corner_advance_distance:
            # Do not aim around a sharp corner before actually approaching it.
            lookahead = min(lookahead, vertex_distance)
        distance_along = 0.0
        for index in range(best_segment, len(path) - 1):
            start = projection if index == best_segment else path[index]
            end = path[index + 1]
            segment_length = start.distance(end)
            if distance_along + segment_length >= lookahead - 1e-12:
                fraction = 0.0 if segment_length == 0 else (lookahead - distance_along) / segment_length
                target = Point(start.x + fraction * (end.x - start.x), start.y + fraction * (end.y - start.y))
                break
            distance_along += segment_length
        heading = math.atan2(target.y - position.y, target.x - position.x)
        heading_error = wrap_angle(heading - pose.yaw)
        target_distance = max(position.distance(target), 1e-6)
        curvature = 2.0 * math.sin(heading_error) / target_distance
        speed = self.limits.max_autonomy_speed_mps / (1.0 + self.config.curvature_slowdown * abs(curvature))
        speed *= max(0.0, math.cos(heading_error))
        approach_speed = math.sqrt(2.0 * self.limits.max_deceleration_mps2 * max(0.0, goal_distance - self.config.goal_tolerance_m * 0.5))
        speed = min(speed, max(self.config.minimum_approach_speed_mps, approach_speed))
        if sharp_corner:
            vertex_approach_speed = math.sqrt(2.0 * self.limits.max_deceleration_mps2 *
                                               max(0.0, vertex_distance - corner_advance_distance * 0.5))
            speed = min(speed, max(self.config.minimum_approach_speed_mps, vertex_approach_speed))
        # Align before translation for large heading changes. The threshold also
        # covers the exact +/-90 degree boundary without tiny-cosine translation.
        if abs(heading_error) >= _ALIGNMENT_THRESHOLD_RAD - 1e-12:
            speed = 0.0
        yaw_rate = speed * curvature
        if speed == 0.0:
            yaw_rate = math.copysign(self.limits.max_yaw_rate_rps, heading_error)
        return TrackingResult(
            Command(clamp(speed, -self.limits.max_autonomy_speed_mps, self.limits.max_autonomy_speed_mps),
                    clamp(yaw_rate, -self.limits.max_yaw_rate_rps, self.limits.max_yaw_rate_rps)),
            False, target, curvature, best_distance,
        )


__all__ = ["PurePursuitTracker", "TrackingResult", "path_length"]
