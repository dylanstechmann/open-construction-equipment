# SPDX-License-Identifier: Apache-2.0
"""Strict standard-library loaders for simulation and mission JSON.

JSON Schema documents are supplied for interchange, but runtime validation is
implemented here so normal use has no third-party dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any

from .geometry import Circle, Point, is_simple_polygon, point_in_polygon
from .models import Pose


class ConfigError(ValueError):
    """A malformed, inconsistent, or unsafe simulation input."""


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{name} must be an object")
    return value


def _keys(data: dict[str, Any], required: set[str], optional: set[str], name: str) -> None:
    missing = required - data.keys()
    unknown = data.keys() - required - optional
    if missing:
        raise ConfigError(f"{name} missing fields: {', '.join(sorted(missing))}")
    if unknown:
        raise ConfigError(f"{name} unknown fields: {', '.join(sorted(unknown))}")


def _number(data: dict[str, Any], key: str, name: str, low: float | None = None, high: float | None = None,
            strict_low: bool = False) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{name}.{key} must be a finite number")
    try:
        result = float(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise ConfigError(f"{name}.{key} must be a finite number") from exc
    if not math.isfinite(result):
        raise ConfigError(f"{name}.{key} must be a finite number")
    if low is not None and (result <= low if strict_low else result < low):
        relation = ">" if strict_low else ">="
        raise ConfigError(f"{name}.{key} must be {relation} {low}")
    if high is not None and result > high:
        raise ConfigError(f"{name}.{key} must be <= {high}")
    return result


def _string(data: dict[str, Any], key: str, name: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{name}.{key} must be a non-empty string")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ConfigError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ConfigError(f"non-standard JSON numeric constant: {value}")


def load_json(path: str | Path) -> dict[str, Any]:
    """Load one strict JSON object, rejecting duplicates and NaN/Infinity."""
    source = Path(path)
    try:
        with source.open(encoding="utf-8") as handle:
            value = json.load(handle, object_pairs_hook=_unique_object,
                              parse_constant=_reject_json_constant)
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"cannot load {source}: {exc}") from exc
    return _mapping(value, str(source))


@dataclass(frozen=True)
class MachineConfig:
    width_m: float
    mass_kg: float
    footprint_length_m: float
    footprint_radius_m: float
    track_gauge_m: float


@dataclass(frozen=True)
class LimitConfig:
    max_manual_speed_mps: float
    max_autonomy_speed_mps: float
    max_acceleration_mps2: float
    max_deceleration_mps2: float
    max_yaw_rate_rps: float
    max_yaw_acceleration_rps2: float
    max_tilt_rad: float


@dataclass(frozen=True)
class ControlConfig:
    period_s: float
    heartbeat_timeout_s: float
    localization_timeout_s: float


@dataclass(frozen=True)
class TrackerConfig:
    lookahead_m: float
    goal_tolerance_m: float
    curvature_slowdown: float
    minimum_approach_speed_mps: float


@dataclass(frozen=True)
class BatteryConfig:
    nominal_energy_kwh: float
    initial_charge_fraction: float
    auxiliary_power_kw: float
    drive_power_kw_at_1mps: float
    turn_power_kw_at_1rps: float


@dataclass(frozen=True)
class SimulationConfig:
    machine: MachineConfig
    limits: LimitConfig
    control: ControlConfig
    tracker: TrackerConfig
    battery: BatteryConfig


@dataclass(frozen=True)
class MissionConfig:
    name: str
    geofence: tuple[Point, ...]
    obstacles: tuple[Circle, ...]
    start: Pose
    goal: Pose
    grid_resolution_m: float
    safety_margin_m: float
    max_duration_s: float


def load_simulation_config(path: str | Path) -> SimulationConfig:
    data = load_json(path)
    _keys(data, {"platform", "simulationOnly", "machine", "limits", "control", "tracker", "battery"},
          {"schemaVersion", "spdxLicenseIdentifier", "provenance", "valueStatus"}, "simulation")
    if data["platform"] != "OCE-CTL-01" or data["simulationOnly"] is not True:
        raise ConfigError("simulation.platform must be OCE-CTL-01 and simulationOnly must be true")
    machine_data = _mapping(data["machine"], "machine")
    _keys(machine_data, {"width_m", "mass_kg", "footprint_length_m", "footprint_radius_m", "track_gauge_m"}, set(), "machine")
    machine = MachineConfig(
        width_m=_number(machine_data, "width_m", "machine", 0, strict_low=True),
        mass_kg=_number(machine_data, "mass_kg", "machine", 0, strict_low=True),
        footprint_length_m=_number(machine_data, "footprint_length_m", "machine", 0, strict_low=True),
        footprint_radius_m=_number(machine_data, "footprint_radius_m", "machine", 0, strict_low=True),
        track_gauge_m=_number(machine_data, "track_gauge_m", "machine", 0, strict_low=True),
    )
    required_radius = math.hypot(machine.footprint_length_m / 2.0, machine.width_m / 2.0)
    if machine.footprint_radius_m + 1e-9 < required_radius:
        raise ConfigError(f"machine.footprint_radius_m must enclose the rectangular footprint (>= {required_radius:.6f})")
    limits_data = _mapping(data["limits"], "limits")
    names = {"max_manual_speed_mps", "max_autonomy_speed_mps", "max_acceleration_mps2", "max_deceleration_mps2",
             "max_yaw_rate_rps", "max_yaw_acceleration_rps2", "max_tilt_deg"}
    _keys(limits_data, names, set(), "limits")
    limits = LimitConfig(
        max_manual_speed_mps=_number(limits_data, "max_manual_speed_mps", "limits", 0, strict_low=True),
        max_autonomy_speed_mps=_number(limits_data, "max_autonomy_speed_mps", "limits", 0, strict_low=True),
        max_acceleration_mps2=_number(limits_data, "max_acceleration_mps2", "limits", 0, strict_low=True),
        max_deceleration_mps2=_number(limits_data, "max_deceleration_mps2", "limits", 0, strict_low=True),
        max_yaw_rate_rps=_number(limits_data, "max_yaw_rate_rps", "limits", 0, strict_low=True),
        max_yaw_acceleration_rps2=_number(limits_data, "max_yaw_acceleration_rps2", "limits", 0, strict_low=True),
        max_tilt_rad=math.radians(_number(limits_data, "max_tilt_deg", "limits", 0, 45, strict_low=True)),
    )
    if limits.max_autonomy_speed_mps > limits.max_manual_speed_mps:
        raise ConfigError("limits.max_autonomy_speed_mps cannot exceed the manual concept limit")
    control_data = _mapping(data["control"], "control")
    _keys(control_data, {"period_s", "heartbeat_timeout_s", "localization_timeout_s"}, set(), "control")
    control = ControlConfig(
        period_s=_number(control_data, "period_s", "control", 0.001, 1.0, strict_low=True),
        heartbeat_timeout_s=_number(control_data, "heartbeat_timeout_s", "control", 0, strict_low=True),
        localization_timeout_s=_number(control_data, "localization_timeout_s", "control", 0, strict_low=True),
    )
    if control.heartbeat_timeout_s < control.period_s or control.localization_timeout_s < control.period_s:
        raise ConfigError("control timeouts must be at least one control period")
    tracker_data = _mapping(data["tracker"], "tracker")
    _keys(tracker_data, {"lookahead_m", "goal_tolerance_m", "curvature_slowdown", "minimum_approach_speed_mps"}, set(), "tracker")
    tracker = TrackerConfig(
        lookahead_m=_number(tracker_data, "lookahead_m", "tracker", 0, strict_low=True),
        goal_tolerance_m=_number(tracker_data, "goal_tolerance_m", "tracker", 0, strict_low=True),
        curvature_slowdown=_number(tracker_data, "curvature_slowdown", "tracker", 0),
        minimum_approach_speed_mps=_number(tracker_data, "minimum_approach_speed_mps", "tracker", 0),
    )
    if tracker.minimum_approach_speed_mps > limits.max_autonomy_speed_mps:
        raise ConfigError("tracker.minimum_approach_speed_mps exceeds autonomy speed")
    battery_data = _mapping(data["battery"], "battery")
    battery_names = {"nominal_energy_kwh", "initial_charge_fraction", "auxiliary_power_kw", "drive_power_kw_at_1mps", "turn_power_kw_at_1rps"}
    _keys(battery_data, battery_names, set(), "battery")
    battery = BatteryConfig(
        nominal_energy_kwh=_number(battery_data, "nominal_energy_kwh", "battery", 0, strict_low=True),
        initial_charge_fraction=_number(battery_data, "initial_charge_fraction", "battery", 0, 1, strict_low=True),
        auxiliary_power_kw=_number(battery_data, "auxiliary_power_kw", "battery", 0),
        drive_power_kw_at_1mps=_number(battery_data, "drive_power_kw_at_1mps", "battery", 0),
        turn_power_kw_at_1rps=_number(battery_data, "turn_power_kw_at_1rps", "battery", 0),
    )
    return SimulationConfig(machine, limits, control, tracker, battery)


def _point(data: Any, name: str) -> Point:
    if not isinstance(data, list) or len(data) != 2:
        raise ConfigError(f"{name} must be [x_m, y_m]")
    wrapped = {"x": data[0], "y": data[1]}
    return Point(_number(wrapped, "x", name), _number(wrapped, "y", name))


def _pose(data: Any, name: str) -> Pose:
    value = _mapping(data, name)
    _keys(value, {"x_m", "y_m", "yaw_rad"}, set(), name)
    return Pose(_number(value, "x_m", name), _number(value, "y_m", name), _number(value, "yaw_rad", name))


def load_mission_config(path: str | Path) -> MissionConfig:
    data = load_json(path)
    _keys(data, {"name", "platform", "simulationOnly", "geofence", "obstacles", "start", "goal", "grid_resolution_m", "safety_margin_m", "max_duration_s"},
          {"schemaVersion", "spdxLicenseIdentifier", "syntheticNotice"}, "mission")
    if data["platform"] != "OCE-CTL-01" or data["simulationOnly"] is not True:
        raise ConfigError("mission.platform must be OCE-CTL-01 and simulationOnly must be true")
    raw_fence = data["geofence"]
    if not isinstance(raw_fence, list) or len(raw_fence) < 3:
        raise ConfigError("mission.geofence needs at least three vertices")
    fence = tuple(_point(item, f"geofence[{index}]") for index, item in enumerate(raw_fence))
    if not is_simple_polygon(fence):
        raise ConfigError("mission.geofence must be a simple non-self-intersecting ring")
    area = sum(a.x * b.y - b.x * a.y for a, b in zip(fence, fence[1:] + fence[:1]))
    if abs(area) < 1e-9:
        raise ConfigError("mission.geofence must have non-zero area")
    raw_obstacles = data["obstacles"]
    if not isinstance(raw_obstacles, list):
        raise ConfigError("mission.obstacles must be an array")
    obstacles = []
    obstacle_ids: set[str] = set()
    for index, item in enumerate(raw_obstacles):
        obstacle = _mapping(item, f"obstacles[{index}]")
        _keys(obstacle, {"id", "center", "radius_m"}, set(), f"obstacles[{index}]")
        obstacle_id = _string(obstacle, "id", f"obstacles[{index}]")
        if obstacle_id in obstacle_ids:
            raise ConfigError(f"duplicate obstacle id {obstacle_id}")
        obstacle_ids.add(obstacle_id)
        obstacles.append(Circle(_point(obstacle["center"], f"obstacles[{index}].center"),
                                _number(obstacle, "radius_m", f"obstacles[{index}]", 0, strict_low=True)))
    start, goal = _pose(data["start"], "start"), _pose(data["goal"], "goal")
    if not point_in_polygon(Point(start.x, start.y), fence) or not point_in_polygon(Point(goal.x, goal.y), fence):
        raise ConfigError("mission start and goal must be inside the geofence")
    resolution = _number(data, "grid_resolution_m", "mission", 0.01, 10.0, strict_low=True)
    margin = _number(data, "safety_margin_m", "mission", 0, 10.0)
    duration = _number(data, "max_duration_s", "mission", 0.1, 86400.0, strict_low=True)
    return MissionConfig(_string(data, "name", "mission"), fence, tuple(obstacles), start, goal, resolution, margin, duration)
