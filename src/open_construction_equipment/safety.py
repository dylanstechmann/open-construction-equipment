# SPDX-License-Identifier: Apache-2.0
"""Non-certified supervisory gate; never an independent protective function."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math

from .config import ControlConfig, LimitConfig
from .geometry import Circle, Point, circle_in_polygon, clamp, obstacle_clearance
from .models import Command, Telemetry


class SupervisorState(StrEnum):
    DISABLED = "disabled"
    ARMED = "armed"
    STOPPED = "stopped"
    FAULT = "fault"


class Reason(StrEnum):
    DISABLED = "DISABLED"
    ARMED = "ARMED"
    OK = "OK"
    ESTOP = "ESTOP"
    PROTECTIVE_FAULT = "PROTECTIVE_FAULT"
    HUMAN_PAUSE = "HUMAN_PAUSE"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"
    STALE_HEARTBEAT = "STALE_HEARTBEAT"
    STALE_LOCALIZATION = "STALE_LOCALIZATION"
    INVALID_TELEMETRY = "INVALID_TELEMETRY"
    INVALID_COMMAND = "INVALID_COMMAND"
    INVALID_TIME = "INVALID_TIME"
    GEOFENCE_VIOLATION = "GEOFENCE_VIOLATION"
    OBSTACLE_CLEARANCE = "OBSTACLE_CLEARANCE"
    TILT_LIMIT = "TILT_LIMIT"
    ARM_REQUIRES_ZERO = "ARM_REQUIRES_ZERO"
    RESET_REQUIRES_ZERO = "RESET_REQUIRES_ZERO"
    RESET_CAUSE_ACTIVE = "RESET_CAUSE_ACTIVE"
    RESET_COMPLETE = "RESET_COMPLETE"
    COMMAND_SATURATED = "COMMAND_SATURATED"


@dataclass(frozen=True)
class SafetyDecision:
    state: SupervisorState
    command: Command
    reasons: tuple[str, ...]
    event: bool


class SafetySupervisor:
    """Latching reference gate with no authority over a real protective chain."""

    def __init__(self, limits: LimitConfig, control: ControlConfig, footprint_radius: float,
                 geofence: tuple[Point, ...], obstacles: tuple[Circle, ...] = (), clearance_margin: float = 0.0):
        self.limits, self.control = limits, control
        self.footprint_radius, self.geofence, self.obstacles = footprint_radius, geofence, obstacles
        self.clearance_margin = clearance_margin
        self.state = SupervisorState.DISABLED
        self._latched: tuple[str, ...] = (Reason.DISABLED.value,)

    @staticmethod
    def _finite_telemetry(telemetry: Telemetry) -> bool:
        return all(math.isfinite(value) for value in (
            telemetry.stamp, telemetry.pose.x, telemetry.pose.y, telemetry.pose.yaw,
            telemetry.speed, telemetry.yaw_rate, telemetry.tilt,
        ))

    def _active_causes(self, requested: Command, telemetry: Telemetry, heartbeat_age: float,
                       localization_age: float, estop: bool, protective_fault: bool,
                       pause: bool, manual_override: bool) -> list[str]:
        causes: list[str] = []
        finite_ages = all(isinstance(age, (int, float)) and not isinstance(age, bool) and math.isfinite(age) and age >= 0
                          for age in (heartbeat_age, localization_age))
        finite_command = all(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
                             for value in (requested.speed, requested.yaw_rate))
        if estop:
            causes.append(Reason.ESTOP.value)
        if protective_fault:
            causes.append(Reason.PROTECTIVE_FAULT.value)
        if not self._finite_telemetry(telemetry) or not finite_ages:
            causes.append(Reason.INVALID_TELEMETRY.value)
        if not finite_command:
            causes.append(Reason.INVALID_COMMAND.value)
        # Avoid geometric operations on poisoned telemetry.
        if self._finite_telemetry(telemetry):
            if heartbeat_age > self.control.heartbeat_timeout_s:
                causes.append(Reason.STALE_HEARTBEAT.value)
            if localization_age > self.control.localization_timeout_s:
                causes.append(Reason.STALE_LOCALIZATION.value)
            position = Point(telemetry.pose.x, telemetry.pose.y)
            if not circle_in_polygon(position, self.footprint_radius, self.geofence):
                causes.append(Reason.GEOFENCE_VIOLATION.value)
            if obstacle_clearance(position, self.footprint_radius + self.clearance_margin, self.obstacles) < 0:
                causes.append(Reason.OBSTACLE_CLEARANCE.value)
            if abs(telemetry.tilt) > self.limits.max_tilt_rad:
                causes.append(Reason.TILT_LIMIT.value)
        if pause:
            causes.append(Reason.HUMAN_PAUSE.value)
        if manual_override:
            causes.append(Reason.MANUAL_OVERRIDE.value)
        return causes

    def update(self, *, requested: Command, telemetry: Telemetry, heartbeat_age: float,
               localization_age: float, estop: bool = False, protective_fault: bool = False,
               pause: bool = False, manual_override: bool = False, arm_request: bool = False,
               reset_request: bool = False) -> SafetyDecision:
        previous = (self.state, self._latched)
        causes = self._active_causes(requested, telemetry, heartbeat_age, localization_age,
                                     estop, protective_fault, pause, manual_override)
        latching = set(causes) - {Reason.HUMAN_PAUSE.value, Reason.MANUAL_OVERRIDE.value}
        if latching:
            self.state = SupervisorState.FAULT
            self._latched = tuple(dict.fromkeys(causes))
        elif causes:
            self.state = SupervisorState.STOPPED
            self._latched = tuple(dict.fromkeys(causes))
        elif reset_request:
            if self.state not in (SupervisorState.STOPPED, SupervisorState.FAULT):
                self._latched = (Reason.DISABLED.value,)
            elif not requested.is_zero():
                self._latched = (Reason.RESET_REQUIRES_ZERO.value,)
            else:
                self.state = SupervisorState.DISABLED
                self._latched = (Reason.RESET_COMPLETE.value,)
        elif self.state in (SupervisorState.STOPPED, SupervisorState.FAULT):
            pass  # Cause clearing never resets or resumes automatically.
        elif self.state == SupervisorState.DISABLED:
            if arm_request:
                if requested.is_zero():
                    self.state = SupervisorState.ARMED
                    self._latched = (Reason.ARMED.value,)
                else:
                    self._latched = (Reason.ARM_REQUIRES_ZERO.value,)
            else:
                self._latched = (Reason.DISABLED.value,)
        if self.state != SupervisorState.ARMED:
            command = Command()
            event = previous != (self.state, self._latched)
            return SafetyDecision(self.state, command, self._latched, event)
        bounded = Command(
            clamp(requested.speed, -self.limits.max_autonomy_speed_mps, self.limits.max_autonomy_speed_mps),
            clamp(requested.yaw_rate, -self.limits.max_yaw_rate_rps, self.limits.max_yaw_rate_rps),
        )
        reasons = [Reason.OK.value]
        if bounded != requested:
            reasons.append(Reason.COMMAND_SATURATED.value)
        self._latched = tuple(reasons)
        event = previous != (self.state, self._latched)
        return SafetyDecision(self.state, bounded, self._latched, event)
