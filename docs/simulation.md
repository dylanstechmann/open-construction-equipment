<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Deterministic simulation reference

**Boundary:** all execution is on a host against synthetic data. There is no hardware I/O, real actuation, controller flashing, deployment interface, or physical-validation claim.

## Units and inputs

The loaders in `src/open_construction_equipment/config.py` use SI units: metres (`_m`), seconds (`_s`), kilograms (`_kg`), radians (`_rad`), metres/second (`_mps`), radians/second (`_rps`), kilowatts (`_kw`), and kilowatt-hours (`_kwh`). Yaw is counter-clockwise in a fixed synthetic planar frame. ISO timestamps in maintenance data must include a UTC offset.

`configs/ctl01.simulation.json` contains **initial AI-authored assumptions; owner review pending**. Width, mass, battery and 6 km/h manual speed align with approximate concept targets. Autonomy is limited to 0.8 m/s, below that manual target. The circular radius encloses the assumed rectangular footprint. Limits, timeouts, tracking parameters and simple power coefficients are not measured machine values.

The loader rejects unknown/missing required fields, Booleans masquerading as numbers, non-finite or out-of-range values, an inadequate footprint radius, autonomy speed above the manual target, invalid timeouts, degenerate or self-intersecting fences and out-of-fence endpoints. Schemas in `schemas/` document interchange. Runtime does **not** use an external JSON Schema implementation; the internal loader supplies required and cross-field validation without dependencies.

## Model

`KinematicSimulator` integrates a constant-twist unicycle/skid-steer approximation with a trapezoidal average of bounded speed and yaw rate. Linear acceleration applies when increasing speed magnitude in the current direction; deceleration applies to braking and reversal. A direction reversal brakes to zero before opposite acceleration begins on a later step. Speed, yaw acceleration and yaw rate are saturated to configured limits. The timestep must be finite, positive and no greater than two control periods.

This is **not a validated dynamics model**. It omits track slip, soil interaction, suspension, mass transfer, attachments, braking distance, stability, hydraulic loads, actuator faults, thermal limits, latency and sensor error. Battery use is only a configurable affine power bookkeeping term based on absolute synthetic speed/yaw rate; operating hours are elapsed simulated step time. Neither predicts endurance, range, thermal behavior or safe machine performance.

## Mission and output

`oce simulate` loads a synthetic polygon fence and circular static obstacles, plans, tracks, supervises and integrates at the control period. `succeeded` requires the supervisor to remain armed and the tracker to enter goal tolerance. Exact initial goal equality succeeds with zero steps. Other statuses are `no_path`, `stopped` and `timeout`; safety events are retained rather than hidden to obtain success.

Mission time never exceeds `max_duration_s`: when the limit is not a whole multiple of the control period, the simulator takes one deterministic shorter final step (for example, 0.1 + 0.1 + 0.05 s for a 0.25 s limit at a 0.1 s period). A shorter-than-period limit therefore produces one partial step unless the goal is already reached. Goal/safety decisions occur at step boundaries; no continuous-time collision or stopping-distance claim is made.

The default writes `builds/demo/result.json` and `builds/demo/trajectory.svg`. JSON includes termination reasons, event log, planner counts, initial/final poses, planned and actual paths, path lengths, goal error, duration, steps, energy bookkeeping and operating hours. SVG embeds its geometry/style and needs no external asset. Both are deterministic for identical inputs. `builds/` is ignored.

## What any far-future physical integration would require

A separately authorized engineering program would still need an approved operational design domain, validated real-time clock/localization and perception, a specified kinematic/dynamic model with measured evidence, actuator/braking/load-holding analysis, fault injection, independent protective functions, communications and timing assurance, cybersecurity, configuration control, signed reviews and applicable legal/site gates. A ROS 2 adapter would be ordinary non-protective software only. No adapter, pin mapping, controller image or field procedure is supplied here.
