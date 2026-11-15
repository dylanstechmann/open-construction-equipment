# SPDX-License-Identifier: Apache-2.0
"""Deterministic unicycle approximation, not a validated dynamics model."""

from __future__ import annotations

import math

from .config import SimulationConfig
from .geometry import clamp, wrap_angle
from .models import Command, Pose, Telemetry


class KinematicSimulator:
    """Exact constant-twist planar integration with bounded synthetic energy use.

    Track slip, soil, load, braking, stability, hydraulics, thermal behavior and
    battery dynamics are deliberately not represented.
    """

    def __init__(self, config: SimulationConfig, initial_pose: Pose):
        self.config = config
        self.stamp = 0.0
        self.speed = 0.0
        self.yaw_rate = 0.0
        self.pose = initial_pose
        self.energy_used_kwh = 0.0
        self.operating_hours = 0.0

    @property
    def charge_fraction(self) -> float:
        return max(0.0, self.config.battery.initial_charge_fraction - self.energy_used_kwh / self.config.battery.nominal_energy_kwh)

    def telemetry(self) -> Telemetry:
        return Telemetry(self.stamp, self.pose, self.speed, self.yaw_rate)

    def step(self, command: Command, dt: float | None = None) -> Telemetry:
        dt = self.config.control.period_s if dt is None else dt
        if not math.isfinite(dt) or dt <= 0 or dt > 2.0 * self.config.control.period_s:
            raise ValueError("dt must be finite, positive, and no more than two control periods")
        if not all(math.isfinite(value) for value in (command.speed, command.yaw_rate)):
            raise ValueError("simulator command must be finite")
        limits = self.config.limits
        same_direction = self.speed == 0.0 or self.speed * command.speed > 0.0
        increasing_magnitude = same_direction and abs(command.speed) > abs(self.speed)
        rate_limit = limits.max_acceleration_mps2 if increasing_magnitude else limits.max_deceleration_mps2
        speed_delta = clamp(command.speed - self.speed, -rate_limit * dt, rate_limit * dt)
        next_speed = clamp(self.speed + speed_delta, -limits.max_autonomy_speed_mps, limits.max_autonomy_speed_mps)
        # A reversal first brakes to zero; opposite acceleration begins next step.
        if self.speed * next_speed < 0.0:
            next_speed = 0.0
        yaw_delta = clamp(command.yaw_rate - self.yaw_rate,
                          -limits.max_yaw_acceleration_rps2 * dt, limits.max_yaw_acceleration_rps2 * dt)
        next_yaw_rate = clamp(self.yaw_rate + yaw_delta, -limits.max_yaw_rate_rps, limits.max_yaw_rate_rps)
        average_speed, average_yaw = (self.speed + next_speed) / 2.0, (self.yaw_rate + next_yaw_rate) / 2.0
        x, y, yaw = self.pose.x, self.pose.y, self.pose.yaw
        if abs(average_yaw) < 1e-9:
            x += average_speed * math.cos(yaw) * dt
            y += average_speed * math.sin(yaw) * dt
        else:
            next_yaw = yaw + average_yaw * dt
            x += average_speed / average_yaw * (math.sin(next_yaw) - math.sin(yaw))
            y -= average_speed / average_yaw * (math.cos(next_yaw) - math.cos(yaw))
        self.pose = Pose(x, y, wrap_angle(yaw + average_yaw * dt))
        self.speed, self.yaw_rate = next_speed, next_yaw_rate
        self.stamp += dt
        self.operating_hours += dt / 3600.0
        battery = self.config.battery
        power_kw = battery.auxiliary_power_kw + abs(average_speed) * battery.drive_power_kw_at_1mps + abs(average_yaw) * battery.turn_power_kw_at_1rps
        self.energy_used_kwh = min(battery.initial_charge_fraction * battery.nominal_energy_kwh,
                                   self.energy_used_kwh + power_kw * dt / 3600.0)
        return self.telemetry()
