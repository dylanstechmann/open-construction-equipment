# SPDX-License-Identifier: Apache-2.0
"""Small immutable SI-unit value objects shared by the reference stack."""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Pose:
    """Planar pose: metres and radians, with positive yaw counter-clockwise."""

    x: float
    y: float
    yaw: float


@dataclass(frozen=True)
class Command:
    """Supervisory body-frame speed (m/s) and yaw rate (rad/s)."""

    speed: float = 0.0
    yaw_rate: float = 0.0

    def is_zero(self, tolerance: float = 1e-12) -> bool:
        return abs(self.speed) <= tolerance and abs(self.yaw_rate) <= tolerance


@dataclass(frozen=True)
class Telemetry:
    """Synthetic localization/motion sample; timestamps are monotonic seconds."""

    stamp: float
    pose: Pose
    speed: float
    yaw_rate: float
    tilt: float = 0.0


@dataclass(frozen=True)
class PathMetrics:
    planned_length_m: float
    driven_length_m: float
    final_goal_error_m: float
    duration_s: float
    energy_used_kwh: float
    operating_hours: float
