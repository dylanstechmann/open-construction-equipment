<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Planning, tracking and supervisory gate

This is an executable learning reference for **OCE-CTL-01**, not a certified safety function or an operational autonomy stack.

## A* planner

`planning.py` builds an occupancy grid from a polygon geofence and static circular obstacles. A cell is free only when the center of a circle with radius `machine footprint radius + mission safety margin` is wholly within the fence and clear of every obstacle. Every actual grid edge and every exact start/goal connector must additionally pass a continuous swept-circle check against all fence edges and inflated obstacles. Motion is 8-connected. Diagonal grid moves and endpoint connectors require both adjacent cardinal cells to be free, preventing corner cutting.

Cardinal moves cost 1 and diagonal moves cost √2 in grid units. A* estimates the remaining cost with the straight-line distance from the cell center to the exact goal, divided by the grid resolution. This takes one distance calculation per estimate. Every route is at least this long, and a cell with a clear goal connector can reach the goal for exactly this cost. Heap ordering and fixed neighbor order provide deterministic tie-breaking. Visible free cell centers provide multi-source/multi-destination endpoint connections. Exact start/goal equality returns a one-point plan and immediate mission success; distinct points in one cell return a checked direct path or a visibility-checked detour. If no safe route or connector exists, planning returns `no_path` rather than a colliding path. `start_blocked` and `goal_blocked` remain distinct for physically invalid endpoints and all errors propagate into mission status.

The grid is deliberately conservative and incomplete: it can reject a feasible route when no suitable cell centers/8-connected edges are visible, and center occupancy does not itself certify an edge. Known-static-circular-obstacle and circular-footprint assumptions remain; tracker deviation from a planned line is separately supervised. This is not perception, semantic hazard detection or complete motion planning.

## Pure pursuit

`tracking.py` finds the closest path-segment projection, advances lookahead distance from that projection, computes signed curvature, and emits body speed/yaw rate. A direction change greater than 30° is treated as a sharp corner: lookahead remains capped to the incoming segment until its endpoint is approached, rather than aiming unconstrained around the vertex. The advance zone is the smaller of one quarter of the configured lookahead and goal tolerance. A braking-distance calculation reduces speed near sharp vertices, subject to the existing minimum approach speed.

Heading error at or beyond ±60° produces bounded rotation without translation while the vehicle aligns; this includes the exact ±90° floating-point boundary. After the vertex approach zone, lookahead can advance to the outgoing segment. Speed is also reduced for curvature and goal approach. Commands are bounded by autonomy speed/yaw limits and entering goal tolerance emits zero. A one-point path is accepted only when already at the goal. The tracker has no authority to arm or resume the machine model.

The 30°/60° and advance-zone choices are deterministic tracking heuristics, not validated control parameters. Pure pursuit still has tracking error, closest-segment selection can be ambiguous on unusual/self-crossing paths, and a clear planned polyline does not guarantee that the simulated pose remains on it. Nominal corner and coarse-grid tests check progress, bounded excursion and sampled clearance only; they are not exact path-containment, continuous-collision or general safety proofs. The independent supervisor and its geometry/margin checks remain unchanged.

## Independent supervisory gate

`safety.py` does not call the tracker and receives proposed commands only as input. Its states are:

| State | Meaning | Command |
|---|---|---|
| `disabled` | Initial/reset state; zero-command explicit arm required | zero |
| `armed` | Healthy synthetic supervisory permission only | bounded proposal |
| `stopped` | Latched human pause/manual override | zero |
| `fault` | Latched e-stop/protective, freshness, geometry, tilt or validity fault | zero |

E-stop and protective fault have highest priority. Human pause/manual override always suppresses a proposed command. Non-finite telemetry, command or age, stale heartbeat/localization, full-footprint geofence violation, obstacle-margin violation, or excess tilt forces zero and a latched fault. Equality at a timeout is fresh; exceeding it is stale.

Cause clearing never resumes motion. Reset requires an existing stop/fault, an all-zero requested command and no active cause; it enters `disabled`, not `armed`. Rearm is a separate zero-command request after all preconditions pass. Finite command saturation is reported as `COMMAND_SATURATED` and does not itself create or clear a safety decision.

Structured reason codes include `ESTOP`, `PROTECTIVE_FAULT`, `HUMAN_PAUSE`, `MANUAL_OVERRIDE`, `STALE_HEARTBEAT`, `STALE_LOCALIZATION`, `INVALID_TELEMETRY`, `INVALID_COMMAND`, `GEOFENCE_VIOLATION`, `OBSTACLE_CLEARANCE`, `TILT_LIMIT`, reset/arm errors and `COMMAND_SATURATED`.

## Exact safety boundary

This ordinary Python gate is only a reference supervisory decision point. It is not independent hardware protection, safety-rated logic, a validated stop, an interlock or proof of risk reduction. The independent protective chain described in ADR-0002 remains required for any real design. Simulation cannot demonstrate diagnostic coverage, response time, systematic capability, PL/SIL, braking, residual energy control or safe load holding.
