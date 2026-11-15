# SPDX-License-Identifier: Apache-2.0
"""Headless deterministic mission composition and self-contained reporting."""

from __future__ import annotations

from html import escape
import json
import math
from pathlib import Path
from typing import Any

from .config import MissionConfig, SimulationConfig
from .geometry import Point, path_length
from .models import Command
from .planning import NoPathError, plan_path
from .safety import SafetySupervisor, SupervisorState
from .simulator import KinematicSimulator
from .tracking import PurePursuitTracker

RESULT_SCHEMA_VERSION = "1.0.0"


def _pose_data(pose: Any) -> dict[str, float]:
    return {"x_m": pose.x, "y_m": pose.y, "yaw_rad": pose.yaw}


def _result(mission: MissionConfig, status: str, simulator: KinematicSimulator,
            planned: tuple[Any, ...], actual: list[Any], events: list[dict[str, Any]],
            final_reasons: list[str], planner: dict[str, Any] | None = None) -> dict[str, Any]:
    driven = sum(math.hypot(b.x - a.x, b.y - a.y) for a, b in zip(actual, actual[1:]))
    return {
        "schemaVersion": RESULT_SCHEMA_VERSION,
        "platform": "OCE-CTL-01",
        "simulationOnly": True,
        "evidenceStatus": "SIMULATED_NOT_PHYSICAL_VALIDATION",
        "mission": mission.name,
        "status": status,
        "finalReasons": final_reasons,
        "initialPose": _pose_data(actual[0]),
        "finalPose": _pose_data(actual[-1]),
        "metrics": {
            "plannedLength_m": path_length(planned) if planned else 0.0,
            "drivenLength_m": driven,
            "finalGoalError_m": math.hypot(actual[-1].x - mission.goal.x, actual[-1].y - mission.goal.y),
            "duration_s": simulator.stamp,
            "energyUsed_kwh": simulator.energy_used_kwh,
            "operatingHours": simulator.operating_hours,
            "batteryChargeFraction": simulator.charge_fraction,
            "steps": max(0, len(actual) - 1),
        },
        "planner": planner or {},
        "events": events,
        "plannedPath": [{"x_m": point.x, "y_m": point.y} for point in planned],
        "actualPath": [_pose_data(pose) for pose in actual],
    }


def run_mission(config: SimulationConfig, mission: MissionConfig) -> dict[str, Any]:
    simulator = KinematicSimulator(config, mission.start)
    actual = [mission.start]
    events: list[dict[str, Any]] = []
    start, goal = Point(mission.start.x, mission.start.y), Point(mission.goal.x, mission.goal.y)
    try:
        plan = plan_path(mission.geofence, mission.obstacles, start, goal, mission.grid_resolution_m,
                         config.machine.footprint_radius_m + mission.safety_margin_m)
    except NoPathError as exc:
        events.append({"time_s": 0.0, "type": "termination", "reasons": [exc.reason.upper()]})
        return _result(mission, "no_path", simulator, (), actual, events, [exc.reason.upper()],
                       {"error": str(exc), "resolution_m": mission.grid_resolution_m})
    tracker = PurePursuitTracker(config.tracker, config.limits)
    supervisor = SafetySupervisor(config.limits, config.control, config.machine.footprint_radius_m,
                                  mission.geofence, mission.obstacles, mission.safety_margin_m)
    planner_data = {"algorithm": "8-connected A*", "visitedCells": plan.visited_cells,
                    "blockedCells": plan.blocked_cells, "resolution_m": plan.resolution_m,
                    "inflationRadius_m": plan.inflation_radius_m, "waypoints": len(plan.path)}
    events.append({"time_s": 0.0, "type": "planned", "reasons": [], "waypoints": len(plan.path)})
    telemetry = simulator.telemetry()
    decision = supervisor.update(requested=Command(), telemetry=telemetry, heartbeat_age=0.0,
                                 localization_age=0.0, arm_request=True)
    events.append({"time_s": 0.0, "type": "supervisor", "state": decision.state.value, "reasons": list(decision.reasons)})
    status = "timeout"
    final_reasons = ["TIMEOUT"]
    if len(plan.path) == 1:
        # Exact positional equality is already success; pure pursuit needs no segment.
        status, final_reasons = "succeeded", ["GOAL_REACHED"]
        events.append({"time_s": 0.0, "type": "termination", "reasons": final_reasons})
    else:
        while True:
            telemetry = simulator.telemetry()
            tracking = tracker.update(telemetry.pose, plan.path)
            decision = supervisor.update(requested=tracking.command, telemetry=telemetry,
                                         heartbeat_age=0.0, localization_age=0.0)
            if decision.event:
                events.append({"time_s": simulator.stamp, "type": "supervisor", "state": decision.state.value,
                               "reasons": list(decision.reasons)})
            if decision.state != SupervisorState.ARMED:
                status, final_reasons = "stopped", list(decision.reasons)
                events.append({"time_s": simulator.stamp, "type": "termination", "reasons": final_reasons})
                break
            if tracking.goal_reached:
                status, final_reasons = "succeeded", ["GOAL_REACHED"]
                events.append({"time_s": simulator.stamp, "type": "termination", "reasons": final_reasons})
                break
            if simulator.charge_fraction <= 0.0:
                status, final_reasons = "stopped", ["ENERGY_EXHAUSTED"]
                events.append({"time_s": simulator.stamp, "type": "termination", "reasons": final_reasons})
                break
            remaining = mission.max_duration_s - simulator.stamp
            if remaining <= 0.0:
                events.append({"time_s": simulator.stamp, "type": "termination", "reasons": final_reasons})
                break
            # The final partial step lands exactly on the configured time limit.
            actual.append(simulator.step(decision.command, dt=min(config.control.period_s, remaining)).pose)
    return _result(mission, status, simulator, plan.path, actual, events, final_reasons, planner_data)


def trajectory_svg(result: dict[str, Any], mission: MissionConfig) -> str:
    width, height, margin = 1000, 760, 40
    min_x, max_x = min(p.x for p in mission.geofence), max(p.x for p in mission.geofence)
    min_y, max_y = min(p.y for p in mission.geofence), max(p.y for p in mission.geofence)
    scale = min((width - 2 * margin) / max(max_x - min_x, 1e-9), (height - 2 * margin) / max(max_y - min_y, 1e-9))

    def screen(point: Any) -> tuple[float, float]:
        return margin + (point.x - min_x) * scale, height - margin - (point.y - min_y) * scale

    fence = " ".join(f"{x:.3f},{y:.3f}" for x, y in (screen(p) for p in mission.geofence))
    planned = " ".join(f"{x:.3f},{y:.3f}" for x, y in (screen(Point(item["x_m"], item["y_m"])) for item in result["plannedPath"]))
    actual = " ".join(f"{x:.3f},{y:.3f}" for x, y in (screen(Point(item["x_m"], item["y_m"])) for item in result["actualPath"]))
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="#fafafa"/>',
             '<style>text{font-family:monospace;fill:#17202a}.label{font-size:15px}</style>',
             f'<polygon points="{fence}" fill="#eef5e9" stroke="#263b2d" stroke-width="3"/>']
    for obstacle in mission.obstacles:
        x, y = screen(obstacle.center)
        parts.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{obstacle.radius * scale:.3f}" fill="#d98880" stroke="#7b241c" stroke-width="2"/>')
    parts.extend([f'<polyline points="{planned}" fill="none" stroke="#2874a6" stroke-width="3" stroke-dasharray="8 5"/>',
                  f'<polyline points="{actual}" fill="none" stroke="#7d3c98" stroke-width="3"/>'])
    for key, color, label in (("initialPose", "#1e8449", "START"), ("finalPose", "#17202a", "FINAL")):
        x, y = screen(Point(result[key]["x_m"], result[key]["y_m"]))
        parts.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="7" fill="{color}"/>')
        parts.append(f'<text class="label" x="{x + 10:.3f}" y="{y - 10:.3f}">{label}</text>')
    gx, gy = screen(mission.goal)
    parts.append(f'<circle cx="{gx:.3f}" cy="{gy:.3f}" r="9" fill="none" stroke="#1e8449" stroke-width="3"/>')
    parts.append(f'<text class="label" x="20" y="24">OCE-CTL-01 — SIMULATION ONLY — {escape(mission.name)} — {escape(result["status"])}</text>')
    parts.append('<text class="label" x="20" y="748">Blue dashed: A* plan; purple: simulated trajectory; red: synthetic obstacles. Not physical evidence.</text>')
    parts.append('</svg>')
    return chr(10).join(parts) + chr(10)


def write_mission_outputs(result: dict[str, Any], mission: MissionConfig, output_dir: str | Path) -> tuple[Path, Path]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    result_path, svg_path = directory / "result.json", directory / "trajectory.svg"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + chr(10), encoding="utf-8")
    svg_path.write_text(trajectory_svg(result, mission), encoding="utf-8")
    return result_path, svg_path
