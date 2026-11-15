<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Hydraulic architecture — OCE-CTL-01

## Unreleased concept

A target 10 kW electric motor drives a hydraulic pump for lift and tilt. A controlled valve section directs fluid to lift actuators and tilt actuation; auxiliary flow is outside current operating scope. Filtration, reservoir, cooling, condition monitoring and load-holding/lowering functions are required design topics.

The 10 kW value does not specify pressure or flow. **All pressure/relief/test settings, flows, cylinder dimensions, line sizes, hose construction, port threads, fitting types, fluid specification, filter ratings, cleanliness criteria, cooling capacity and leak limits are TBD.** Never commission using guessed values.

## Safety functions and failure behavior

- Prevent unsafe arm/bucket descent for supply loss, hose failure, valve faults, stopping, shutdown and service. Cylinder-mounted load control versus other architectures is TBD.
- Provide controlled lowering and mechanical arm support for service. A hydraulic valve is not a service support.
- Avoid unintended actuator movement at startup/reset and define pump response to e-stop/fault based on lift-load risk assessment.
- Route hoses away from abrasion, pinch, heat and spray exposure. Guards do not replace correct hose selection/routing.
- Establish lockable isolation, pressure indication and verified depressurization; a gauge reading alone does not prove every trapped volume is empty.
- Specify fluid compatibility, fire/environment considerations, spill handling and skin-injection emergency response in the reviewed manual.

## Thermal and contamination strategy

Derive pump displacement/motor duty from work cycles, pressure/flow and efficiency. Evaluate heat rejection and cold conditions. Reservoir volume, deaeration, suction conditions and access are TBD. Define supplier/assembly cleanliness, flush loop/filter arrangement, sampling points, temporary-jumper restrictions and acceptance criteria from component cleanliness requirements; never substitute a generic flush duration.

Pressure/leak testing needs an approved procedure, calibrated instruments, exclusion zone, suitable medium/guards and limits from released components. Never tighten a connection or search for leaks by hand while pressurized.

## Hose register use

The hose register identifies connection intent and hazards only. Ports/endpoints are functional, not manufacturing locations. Each final line needs drawing ID, endpoints, length, bore/construction, bend radius, pressure evidence, compatibility, fittings, clamps, abrasion protection and replacement criteria after engineering. An abstract circuit ID is not an ordering code.
