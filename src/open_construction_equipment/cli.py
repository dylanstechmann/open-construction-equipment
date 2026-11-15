# SPDX-License-Identifier: Apache-2.0
"""Host-only command-line interface; no hardware I/O or deployment operations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Sequence

from .bom import summarize_bom
from .bunker import load_bunker_input, load_bunker_registers, load_bunker_site, plan_bunker, write_bunker_outputs
from .config import ConfigError, load_mission_config, load_simulation_config
from .engineering import calculate_static_longitudinal, load_analysis_input, write_analysis_result
from .maintenance import evaluate_maintenance, load_service_history, load_service_plan
from .mission import run_mission, write_mission_outputs
from .resources import default_data_root
from .validation import validate_repository


def _emit(data: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, indent=2, sort_keys=True, allow_nan=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="oce", description="OCE-CTL-01 SIMULATION-ONLY host tools; never hardware control.")
    parser.add_argument("--version", action="version", version="oce 0.4.0 (simulation/calculation-only)")
    subcommands = parser.add_subparsers(dest="command", required=True)
    data_root = default_data_root()
    validate = subcommands.add_parser("validate", help="validate source repository or installed runtime data")
    validate.add_argument("--json", action="store_true", help="emit the full validation report as JSON")
    validate.add_argument("--root", type=Path, default=None, help=argparse.SUPPRESS)
    simulate = subcommands.add_parser("simulate", help="run a deterministic synthetic mission on the host")
    simulate.add_argument("--config", type=Path, default=data_root / "configs/ctl01.simulation.json")
    simulate.add_argument("--mission", type=Path, default=data_root / "examples/missions/synthetic-yard.json")
    simulate.add_argument("--output-dir", type=Path, default=Path.cwd() / "builds/demo")
    simulate.add_argument("--json", action="store_true", help="emit the complete result JSON to stdout")
    maintenance = subcommands.add_parser("maintenance", help="calculate due items from proposed intervals and supplied records")
    maintenance.add_argument("--plan", type=Path, default=data_root / "maintenance/ctl01/service-intervals.json")
    maintenance.add_argument("--records", type=Path, default=data_root / "examples/maintenance/synthetic-service-history.json")
    maintenance.add_argument("--json", action="store_true", help="emit the full maintenance report as JSON")
    bom = subcommands.add_parser("bom", help="summarize the concept BOM by subsystem and safety criticality")
    bom.add_argument("--bom", type=Path, default=data_root / "hardware/ctl01/bom/ctl01-bom.csv")
    bom.add_argument("--json", action="store_true", help="emit the full BOM summary as JSON")
    analyze = subcommands.add_parser("analyze", help="run unreviewed synthetic AN-LC-001A static arithmetic")
    analyze.add_argument("--input", type=Path, default=data_root / "examples/analysis/synthetic-lc001.json")
    analyze.add_argument("--output-dir", type=Path, default=Path.cwd() / "builds/analysis/lc001")
    analyze.add_argument("--json", action="store_true", help="emit the complete analysis result JSON to stdout")
    bunker = subcommands.add_parser("bunker", help="calculate a blocked synthetic BUNKER-01 quantity/dependency plan")
    bunker.add_argument("--input", type=Path, default=data_root / "examples/bunker/synthetic-bunker01.json")
    bunker.add_argument("--work-breakdown", type=Path, default=data_root / "projects/bunker01/construction/work-breakdown.csv")
    bunker.add_argument("--quality-gates", type=Path, default=data_root / "projects/bunker01/construction/quality-gates.csv")
    bunker.add_argument("--fleet-register", type=Path, default=data_root / "projects/bunker01/construction/fleet-register.csv")
    bunker.add_argument("--site-inputs", type=Path, default=data_root / "projects/bunker01/site-inputs.json")
    bunker.add_argument("--output-dir", type=Path, default=Path.cwd() / "builds/bunker01")
    bunker.add_argument("--json", action="store_true", help="emit the complete blocked synthetic plan JSON to stdout")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            report = validate_repository(args.root)
            _emit(report, args.json)
            if not args.json:
                label = "Repository validation" if report["fullRepositoryValidation"] else "Package resource validation"
                print(f"{label}: {report['status'].upper()} — {report['jsonFilesChecked']} JSON, {report['csvFilesChecked']} CSV files")
                for error in report["errors"]:
                    print(f"ERROR: {error}", file=sys.stderr)
            return 0 if report["status"] == "passed" else 1
        if args.command == "simulate":
            config, mission = load_simulation_config(args.config), load_mission_config(args.mission)
            result = run_mission(config, mission)
            result_path, svg_path = write_mission_outputs(result, mission, args.output_dir)
            _emit(result, args.json)
            if not args.json:
                print(f"Simulation status: {result['status']} ({', '.join(result['finalReasons'])})")
                print(f"Goal error: {result['metrics']['finalGoalError_m']:.3f} m; duration: {result['metrics']['duration_s']:.1f} s")
                print(f"Reports: {result_path} and {svg_path}")
            return {"succeeded": 0, "no_path": 2, "stopped": 3, "timeout": 4}.get(result["status"], 1)
        if args.command == "maintenance":
            plan, history = load_service_plan(args.plan), load_service_history(args.records)
            report = evaluate_maintenance(plan, history)
            _emit(report, args.json)
            if not args.json:
                print(f"Proposed maintenance review: {report['summary']['overdue'] + report['summary']['due']} overdue/due of {report['summary']['total']} items")
                for item in report["items"]:
                    if item["status"] != "current":
                        print(f"{item['serviceId']}: {item['status']} — {', '.join(item['reasons'])}")
                print("Intervals are proposed, not an OEM schedule; no service completion was invented.")
            return 0
        if args.command == "analyze":
            analysis_input = load_analysis_input(args.input)
            result = calculate_static_longitudinal(analysis_input)
            result_path = write_analysis_result(result, args.output_dir)
            _emit(result, args.json)
            if not args.json:
                values = result["results"]
                print(f"Analysis {result['analysisId']}: total mass {values['totalMass_kg']:.3f} kg; resultant x {values['resultantX_m']:.6f} m")
                print(f"Minimum signed static moment margin: {values['staticMomentMargins_Nm']['minimum']:.3f} N*m")
                print(f"Result: {result_path}")
                print("UNREVIEWED synthetic arithmetic only; acceptance NOT_ASSESSED; no physical validation or operational verdict.")
            return 0
        if args.command == "bunker":
            model = load_bunker_input(args.input)
            registers = load_bunker_registers(args.work_breakdown, args.quality_gates, args.fleet_register)
            site = load_bunker_site(args.site_inputs)
            result = plan_bunker(model, registers, site)
            result_path, svg_path = write_bunker_outputs(result, args.output_dir)
            _emit(result, args.json)
            if not args.json:
                quantities = result["quantities"]
                print(f"BUNKER-01 synthetic duration: {result['schedule']['syntheticDurationHours']:g} h; "
                      f"critical path: {', '.join(result['schedule']['criticalPathPackageIds'])}")
                print(f"Excavation {quantities['geometry']['excavationVolume_m3']:g} m^3; gross concrete "
                      f"{quantities['concrete']['grossVolume_m3']:g} m^3; modeled-only energy "
                      f"{result['energy']['modeledOnlyElectricEnergy_kWh']:g} kWh")
                print(f"Reports: {result_path} and {svg_path}")
                print("SYNTHETIC PLAN — CONSTRUCTION BLOCKED; all human gates unresolved; no physical validation or authorization.")
            return 0
        if args.command == "bom":
            report = summarize_bom(args.bom)
            _emit(report, args.json)
            if not args.json:
                print(f"Concept BOM: {report['itemCount']} items; mixed-unit quantity total {report['totalQuantity']}")
                for subsystem, values in report["bySubsystem"].items():
                    print(f"{subsystem}: {values['items']} items, quantity {values['quantity']}, safety-critical {values['safetyCriticalItems']}")
                print("Concept accounting only; not procurement or fabrication authority.")
            return 0
    except (ConfigError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
