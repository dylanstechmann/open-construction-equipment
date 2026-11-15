# SPDX-License-Identifier: Apache-2.0
import copy
import csv
from dataclasses import FrozenInstanceError
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from open_construction_equipment.bunker import (
    ALLOWED_AUTONOMY_CLASSES,
    BunkerRegisters,
    EnergyAssumption,
    WorkPackage,
    QualityGate,
    bunker_result_json,
    calculate_energy,
    calculate_quantities,
    calculate_schedule,
    load_bunker_input,
    load_bunker_registers,
    load_bunker_site,
    load_work_breakdown,
    parse_bunker_input,
    plan_bunker,
    schedule_svg,
    write_bunker_outputs,
)
from open_construction_equipment.config import ConfigError
from open_construction_equipment.validation import repository_root, validate_bunker_cad_geometry, validate_repository
from tools.check_all import static_openscad_check

ROOT = repository_root()
INPUT = ROOT / "examples/bunker/synthetic-bunker01.json"
CONSTRUCTION = ROOT / "projects/bunker01/construction"
SCHEMA = ROOT / "schemas/bunker-plan.schema.json"


class BunkerTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(INPUT.read_text(encoding="utf-8"))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.temp_path = Path(self.temp.name)
        self.model = parse_bunker_input(copy.deepcopy(self.data))
        self.registers = load_bunker_registers(
            CONSTRUCTION / "work-breakdown.csv",
            CONSTRUCTION / "quality-gates.csv",
            CONSTRUCTION / "fleet-register.csv",
        )
        self.site = load_bunker_site(ROOT / "projects/bunker01/site-inputs.json")

    def result(self):
        return plan_bunker(self.model, self.registers, self.site)

    def write_input(self, data, name="input.json"):
        path = self.temp_path / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def copy_register(self, source_name, mutate):
        source = CONSTRUCTION / source_name
        with source.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames
            rows = list(reader)
        mutate(rows)
        destination = self.temp_path / source_name
        with destination.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        return destination

    def registers_with_work(self, path):
        return load_bunker_registers(path, CONSTRUCTION / "quality-gates.csv", CONSTRUCTION / "fleet-register.csv")

    def test_external_excavation_geometry_matches_independent_arithmetic(self):
        values = calculate_quantities(self.model)["geometry"]
        self.assertEqual(values["externalLength_m"], 4 + 2 * 0.25)
        self.assertEqual(values["externalWidth_m"], 3 + 2 * 0.25)
        self.assertAlmostEqual(values["totalStructureHeight_m"], 0.25 + 2.4 + 0.30)
        self.assertEqual(values["excavationLength_m"], 4.5 + 2 * 0.75)
        self.assertEqual(values["excavationWidth_m"], 3.5 + 2 * 0.75)
        self.assertAlmostEqual(values["excavationDepth_m"], 0.2 + 0.25 + 2.4 + 0.3 + 0.5)
        self.assertEqual(values["externalFootprint_m2"], 15.75)
        self.assertEqual(values["excavationFootprint_m2"], 30)
        self.assertAlmostEqual(values["excavationVolume_m3"], 6 * 5 * 3.65)
        self.assertAlmostEqual(values["enclosureDisplacement_m3"], 4.5 * 3.5 * 2.95)

    def test_floor_roof_wall_shell_and_gross_concrete(self):
        values = calculate_quantities(self.model)["concrete"]
        self.assertEqual(values["floorVolume_m3"], 4.5 * 3.5 * 0.25)
        self.assertEqual(values["roofVolume_m3"], 4.5 * 3.5 * 0.30)
        self.assertEqual(values["wallShellVolume_m3"], 4.5 * 3.5 * 2.4 - 4 * 3 * 2.4)
        self.assertEqual(values["grossVolume_m3"], 3.9375 + 4.725 + 9)
        self.assertEqual(values["grossVolume_m3"], 17.6625)

    def test_concrete_waste_is_theoretical_not_an_order(self):
        values = calculate_quantities(self.model)["concrete"]
        self.assertEqual(values["theoreticalAdjustedVolume_m3"], 17.6625 * 1.05)
        self.assertEqual(values["theoreticalAdjustedVolume_m3"], 18.545625)
        self.assertFalse(values["orderQuantity"])
        self.assertIn("no opening deductions", values["convention"])

    def test_drainage_backfill_and_displacement(self):
        values = calculate_quantities(self.model)["earthworks"]
        self.assertEqual(values["drainageLayerGrossVolume_m3"], 6 * 5 * 0.2)
        self.assertAlmostEqual(values["nominalCompactedBackfillVolume_m3"], 109.5 - 46.4625 - 6)
        self.assertEqual(values["nominalCompactedBackfillVolume_m3"], 57.0375)
        self.assertIn("not a compaction specification", values["convention"])
        self.assertFalse(values["borrowOrHaulDecisionMade"])

    def test_spoil_in_situ_excess_and_haul_off_math(self):
        values = calculate_quantities(self.model)["earthworks"]
        self.assertEqual(values["looseExcavatedSpoilVolume_m3"], 109.5 * 1.25)
        self.assertEqual(values["inSituEquivalentRequiredForBackfill_m3"], 57.0375 / 0.9)
        self.assertEqual(values["inSituEquivalentRequiredForBackfill_m3"], 63.375)
        self.assertAlmostEqual(values["excessInSituVolume_m3"], 109.5 - 63.375)
        self.assertEqual(values["excessLooseHaulOffVolume_m3"], 46.125 * 1.25)
        self.assertEqual(values["excessLooseHaulOffVolume_m3"], 57.65625)
        self.assertEqual(values["mathematicalInSituDeficitVolume_m3"], 0)

    def test_mathematical_borrow_deficit_does_not_make_haul_decision(self):
        self.data["geometry"]["workingSpace_m"] = 0
        self.data["geometry"]["drainageLayer_m"] = 0
        self.data["geometry"]["roofCover_m"] = 100
        values = calculate_quantities(parse_bunker_input(self.data))["earthworks"]
        self.assertGreater(values["inSituEquivalentRequiredForBackfill_m3"], 102.95 * 15.75)
        self.assertLess(values["excessInSituVolume_m3"], 0)
        self.assertGreater(values["mathematicalInSituDeficitVolume_m3"], 0)
        self.assertEqual(values["excessLooseHaulOffVolume_m3"], 0)
        self.assertFalse(values["borrowOrHaulDecisionMade"])

    def test_waterproofing_net_and_waste_area(self):
        values = calculate_quantities(self.model)["waterproofing"]
        expected_net = 4.5 * 3.5 + 2 * (4.5 + 3.5) * 2.95
        self.assertAlmostEqual(values["netArea_m2"], expected_net)
        self.assertAlmostEqual(values["netArea_m2"], 62.95)
        self.assertAlmostEqual(values["wasteAdjustedArea_m2"], 62.95 * 1.10)
        self.assertEqual(values["wasteAdjustedArea_m2"], 69.245)
        self.assertIn("underside excluded", values["convention"])

    def test_zero_cover_working_drainage_and_waste_are_allowed(self):
        for key in ("workingSpace_m", "drainageLayer_m", "roofCover_m"):
            self.data["geometry"][key] = 0
        self.data["wasteModel"]["concreteWasteFraction"] = 0
        self.data["wasteModel"]["waterproofingWasteFraction"] = 0
        values = calculate_quantities(parse_bunker_input(self.data))
        self.assertEqual(values["geometry"]["excavationVolume_m3"], values["geometry"]["enclosureDisplacement_m3"])
        self.assertEqual(values["earthworks"]["drainageLayerGrossVolume_m3"], 0)
        self.assertEqual(values["earthworks"]["nominalCompactedBackfillVolume_m3"], 0)
        self.assertEqual(values["concrete"]["theoreticalAdjustedVolume_m3"], values["concrete"]["grossVolume_m3"])
        self.assertEqual(values["waterproofing"]["wasteAdjustedArea_m2"], values["waterproofing"]["netArea_m2"])

    def test_positive_geometry_rejects_zero_and_negative(self):
        for key in ("internalLength_m", "internalWidth_m", "internalHeight_m", "wallThickness_m", "floorThickness_m", "roofThickness_m"):
            for value in (0, -1):
                with self.subTest(key=key, value=value):
                    data = copy.deepcopy(self.data)
                    data["geometry"][key] = value
                    with self.assertRaises(ConfigError):
                        parse_bunker_input(data)

    def test_geometry_rejects_boolean_nonfinite_and_negative_nonnegative_values(self):
        for value in (True, float("nan"), float("inf"), float("-inf"), -0.1):
            with self.subTest(value=value):
                data = copy.deepcopy(self.data)
                data["geometry"]["workingSpace_m"] = value
                with self.assertRaises(ConfigError):
                    parse_bunker_input(data)

    def test_huge_json_integer_is_controlled_config_error(self):
        self.data["geometry"]["internalLength_m"] = 10**400
        with self.assertRaisesRegex(ConfigError, "finite number"):
            load_bunker_input(self.write_input(self.data))

    def test_external_dimension_overflow_is_controlled(self):
        self.data["geometry"]["internalLength_m"] = 1e308
        self.data["geometry"]["wallThickness_m"] = 1e308
        with self.assertRaisesRegex(ConfigError, "non-finite"):
            calculate_quantities(parse_bunker_input(self.data))

    def test_volume_overflow_is_controlled(self):
        self.data["geometry"]["internalLength_m"] = 1e200
        self.data["geometry"]["internalWidth_m"] = 1e200
        with self.assertRaisesRegex(ConfigError, "non-finite"):
            calculate_quantities(parse_bunker_input(self.data))

    def test_soil_factors_must_be_positive_finite_non_boolean(self):
        for key in ("looseBulkingFactor", "compactedToInSituRatio"):
            for value in (0, -1, True, float("nan"), float("inf"), 10**400):
                with self.subTest(key=key, value=value):
                    data = copy.deepcopy(self.data)
                    data["soilModel"][key] = value
                    with self.assertRaises(ConfigError):
                        parse_bunker_input(data)

    def test_waste_fractions_reject_negative_boolean_and_nonfinite(self):
        for key in ("concreteWasteFraction", "waterproofingWasteFraction"):
            for value in (-0.01, False, float("nan"), float("inf")):
                with self.subTest(key=key, value=value):
                    data = copy.deepcopy(self.data)
                    data["wasteModel"][key] = value
                    with self.assertRaises(ConfigError):
                        parse_bunker_input(data)

    def test_waste_multiplication_overflow_is_controlled(self):
        self.data["wasteModel"]["concreteWasteFraction"] = 1e308
        with self.assertRaises(ConfigError):
            calculate_quantities(parse_bunker_input(self.data))

    def test_models_are_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            self.model.geometry.internalLength_m = 5
        with self.assertRaises(FrozenInstanceError):
            self.registers.packages[0].duration_hours = 99

    def test_provenance_and_safe_statuses_are_mandatory(self):
        self.data["geometry"].pop("provenance")
        with self.assertRaisesRegex(ConfigError, "missing fields: provenance"):
            parse_bunker_input(self.data)
        self.data = json.loads(INPUT.read_text(encoding="utf-8"))
        self.data["soilModel"]["provenance"]["ownerSupplied"] = True
        with self.assertRaisesRegex(ConfigError, "ownerSupplied must be false"):
            parse_bunker_input(self.data)

    def test_no_input_flag_can_override_blocked_baseline(self):
        for key in ("siteKnown", "constructionAuthorized", "physicalValidationPerformed"):
            with self.subTest(key=key):
                data = copy.deepcopy(self.data)
                data[key] = True
                with self.assertRaisesRegex(ConfigError, "no input can authorize|must be false"):
                    parse_bunker_input(data)
        result = self.result()
        self.assertFalse(result["siteKnown"])
        self.assertFalse(result["constructionAuthorized"])
        self.assertFalse(result["physicalValidationPerformed"])
        self.assertTrue(result["syntheticPlanningOnly"])

    def test_schedule_topological_order_precedes_all_dependents(self):
        schedule = calculate_schedule(self.registers)
        positions = {package_id: index for index, package_id in enumerate(schedule["topologicalOrder"])}
        self.assertEqual(len(positions), 22)
        for package in self.registers.packages:
            for dependency in package.dependencies:
                self.assertLess(positions[dependency], positions[package.package_id])
        self.assertEqual(schedule["topologicalOrder"][:2], ["BW-001", "BW-002"])

    def test_schedule_earliest_times_use_maximum_not_sum(self):
        schedule = calculate_schedule(self.registers)
        rows = {row["packageId"]: row for row in schedule["packages"]}
        self.assertEqual(rows["BW-005"]["earliestStartHour"], 80)
        self.assertEqual(rows["BW-011"]["earliestStartHour"], 264)
        self.assertEqual(rows["BW-013"]["earliestStartHour"], 320)
        self.assertEqual(rows["BW-018"]["earliestStartHour"], 408)
        self.assertEqual(rows["BW-020"]["earliestStartHour"], 472)
        self.assertEqual(rows["BW-022"]["earliestFinishHour"], 472)

    def test_zero_duration_human_gates_are_on_critical_path(self):
        schedule = calculate_schedule(self.registers)
        self.assertEqual(schedule["syntheticDurationHours"], 472)
        self.assertEqual(schedule["criticalPathPackageIds"], [
            "BW-001", "BW-002", "BW-003", "BW-005", "BW-006", "BW-007", "BW-008",
            "BW-010", "BW-011", "BW-012", "BW-013", "BW-014", "BW-015", "BW-016",
            "BW-018", "BW-019", "BW-020", "BW-021", "BW-022",
        ])
        for gate in ("BW-013", "BW-020", "BW-021", "BW-022"):
            self.assertIn(gate, schedule["criticalPathPackageIds"])

    def test_autonomy_counts_are_accounting_not_readiness(self):
        counts = calculate_schedule(self.registers)["autonomyClassCounts"]
        self.assertEqual(set(counts), set(ALLOWED_AUTONOMY_CLASSES))
        self.assertEqual(counts, {"human_gate": 6, "specialist": 13, "future_supervised_autonomy": 3, "simulation_candidate": 0})
        self.assertNotIn("percentAutonomous", self.result()["schedule"])

    def test_dependency_cycle_is_rejected(self):
        def mutate(rows):
            rows[0]["dependencies"] = "BW-002"
        path = self.copy_register("work-breakdown.csv", mutate)
        with self.assertRaisesRegex(ConfigError, "cycle"):
            load_work_breakdown(path)

    def test_missing_dependency_is_rejected(self):
        def mutate(rows):
            rows[0]["dependencies"] = "BW-999"
        path = self.copy_register("work-breakdown.csv", mutate)
        with self.assertRaisesRegex(ConfigError, "missing dependency"):
            load_work_breakdown(path)

    def test_missing_required_gate_is_rejected(self):
        def mutate(rows):
            rows[1]["requiredGateIds"] = "BG-999"
        path = self.copy_register("work-breakdown.csv", mutate)
        with self.assertRaisesRegex(ConfigError, "missing gates"):
            self.registers_with_work(path)

    def test_invalid_autonomy_class_is_rejected(self):
        def mutate(rows):
            rows[0]["autonomyClass"] = "autonomous_now"
        path = self.copy_register("work-breakdown.csv", mutate)
        with self.assertRaisesRegex(ConfigError, "unsupported autonomyClass"):
            load_work_breakdown(path)

    def test_resolved_gate_or_evidence_is_rejected(self):
        for key, value in (("status", "RESOLVED"), ("decisionDate", "2026-01-01"), ("reviewer", "Person"), ("signature", "signed"), ("evidenceReference", "evidence")):
            with self.subTest(key=key):
                def mutate(rows):
                    rows[0][key] = value
                gates = self.copy_register("quality-gates.csv", mutate)
                with self.assertRaisesRegex(ConfigError, "UNRESOLVED|must be blank"):
                    load_bunker_registers(CONSTRUCTION / "work-breakdown.csv", gates, CONSTRUCTION / "fleet-register.csv")

    def test_fleet_register_missing_package_reference_is_rejected(self):
        def mutate(rows):
            rows[0]["intendedFutureWorkPackages"] = "BW-999"
        fleet = self.copy_register("fleet-register.csv", mutate)
        with self.assertRaisesRegex(ConfigError, "missing intended packages"):
            load_bunker_registers(CONSTRUCTION / "work-breakdown.csv", CONSTRUCTION / "quality-gates.csv", fleet)

    def test_energy_missing_fleet_and_package_references_are_rejected(self):
        for key, value, message in (("fleetId", "BF-999", "missing fleet"), ("packageId", "BW-999", "missing package")):
            with self.subTest(key=key):
                self.data["energyAssumptions"][0][key] = value
                model = parse_bunker_input(self.data)
                with self.assertRaisesRegex(ConfigError, message):
                    calculate_energy(model, self.registers)

    def test_energy_fleet_must_be_registered_for_package(self):
        self.data["energyAssumptions"][0]["fleetId"] = "BF-006"
        model = parse_bunker_input(self.data)
        with self.assertRaisesRegex(ConfigError, "not registered for intended package"):
            calculate_energy(model, self.registers)

    def test_duplicate_energy_package_fleet_pair_is_rejected(self):
        self.data["energyAssumptions"].append(copy.deepcopy(self.data["energyAssumptions"][0]))
        with self.assertRaisesRegex(ConfigError, "duplicate energy assumption"):
            parse_bunker_input(self.data)

    def test_energy_totals_by_package_and_fleet(self):
        energy = calculate_energy(self.model, self.registers)
        self.assertEqual(energy["modeledOnlyElectricEnergy_kWh"], 246)
        by_package = {row["packageId"]: row["electricEnergy_kWh"] for row in energy["byPackage"]}
        self.assertEqual(by_package["BW-008"], 80)
        self.assertEqual(by_package["BW-020"], 6)
        by_fleet = {row["fleetId"]: row["electricEnergy_kWh"] for row in energy["byFleet"]}
        self.assertEqual(by_fleet["BF-008"], 28)
        self.assertFalse(energy["projectEnergyEstimateAvailable"])

    def test_unmodeled_energy_is_null_not_zero_with_explicit_coverage(self):
        energy = calculate_energy(self.model, self.registers)
        self.assertEqual(len(energy["modeledPackageIds"]), 8)
        self.assertEqual(len(energy["unmodeledPackageIds"]), 14)
        self.assertEqual(energy["unmodeledFleetIds"], ["BF-006"])
        by_package = {row["packageId"]: row["electricEnergy_kWh"] for row in energy["byPackage"]}
        self.assertIsNone(by_package["BW-001"])
        self.assertNotEqual(by_package["BW-001"], 0)
        schedule = {row["packageId"]: row for row in self.result()["schedule"]["packages"]}
        self.assertIsNone(schedule["BW-001"]["modeledElectricEnergy_kWh"])
        self.assertIn("not zero energy", energy["coverageNotice"])

    def test_all_fifteen_gates_block_every_result(self):
        result = self.result()
        self.assertEqual(result["readinessStatus"], "BLOCKED_UNRESOLVED_HUMAN_GATES")
        self.assertEqual(result["unresolvedGateIds"], [f"BG-{index:03d}" for index in range(1, 16)])
        self.assertIn("synthetic planning only", result["planningNotice"])

    def test_svg_has_blocking_label_ids_durations_and_autonomy(self):
        svg = schedule_svg(self.result())
        self.assertIn("SYNTHETIC PLAN — CONSTRUCTION BLOCKED", svg)
        for package_id in ("BW-001", "BW-013", "BW-022"):
            self.assertIn(package_id, svg)
        self.assertIn("human_gate", svg)
        self.assertIn("future_supervised_autonomy", svg)
        self.assertIn("472", svg)
        self.assertNotIn("2026-", svg)
        ET.fromstring(svg)

    def test_svg_escapes_untrusted_register_text(self):
        def mutate(rows):
            rows[0]["name"] = 'Requirements <scope> & "review" — café ⚙'
        work = self.copy_register("work-breakdown.csv", mutate)
        result = plan_bunker(self.model, self.registers_with_work(work), self.site)
        svg = schedule_svg(result)
        self.assertIn("Requirements &lt;scope&gt; &amp; &quot;review&quot; — café ⚙", svg)
        self.assertNotIn("Requirements <scope>", svg)
        ET.fromstring(svg)

    def test_json_and_svg_are_byte_deterministic(self):
        first = self.result()
        second = self.result()
        self.assertEqual(bunker_result_json(first), bunker_result_json(second))
        self.assertEqual(schedule_svg(first), schedule_svg(second))
        output_a = self.temp_path / "a"
        output_b = self.temp_path / "b"
        write_bunker_outputs(first, output_a)
        write_bunker_outputs(second, output_b)
        self.assertEqual((output_a / "result.json").read_bytes(), (output_b / "result.json").read_bytes())
        self.assertEqual((output_a / "schedule.svg").read_bytes(), (output_b / "schedule.svg").read_bytes())

    def test_wrong_csv_row_width_is_controlled(self):
        path = self.temp_path / "wide-work.csv"
        text = (CONSTRUCTION / "work-breakdown.csv").read_text(encoding="utf-8")
        lines = text.splitlines()
        lines[1] += ",unexpected"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "wrong column count"):
            load_work_breakdown(path)

    def test_tiny_compaction_ratio_division_overflow_is_controlled(self):
        self.data["soilModel"]["compactedToInSituRatio"] = 1e-308
        with self.assertRaisesRegex(ConfigError, "non-finite in-situ equivalent backfill"):
            calculate_quantities(parse_bunker_input(self.data))

    def test_modeled_energy_sum_overflow_is_controlled(self):
        for assumption in self.data["energyAssumptions"][:2]:
            assumption["electricEnergy_kWh"] = 1e308
        with self.assertRaisesRegex(ConfigError, "non-finite modeled energy total"):
            calculate_energy(parse_bunker_input(self.data), self.registers)

    def test_schedule_duration_overflow_is_controlled(self):
        def mutate(rows):
            rows[0]["durationHours"] = "1e308"
            rows[1]["durationHours"] = "1e308"
        work = self.copy_register("work-breakdown.csv", mutate)
        with self.assertRaisesRegex(ConfigError, "non-finite package:BW-002 earliest finish"):
            calculate_schedule(self.registers_with_work(work))

    @staticmethod
    def custom_package(package_id, duration, dependencies=(), gate_ids=()):
        return WorkPackage(package_id, f"Package {package_id}", tuple(dependencies), duration, "specialist", "Synthetic role", tuple(gate_ids), "TBD")

    @staticmethod
    def custom_gate(gate_id, producers):
        return QualityGate(gate_id, f"Gate {gate_id}", tuple(producers), "Synthetic evidence", "Responsible human", "UNRESOLVED")

    def test_gate_evidence_delays_consumer_without_ordinary_dependency(self):
        registers = BunkerRegisters(
            (self.custom_package("BW-001", 5), self.custom_package("BW-002", 1, gate_ids=("BG-001",))),
            (self.custom_gate("BG-001", ("BW-001",)),),
            (),
        )
        schedule = calculate_schedule(registers)
        rows = {row["packageId"]: row for row in schedule["packages"]}
        self.assertEqual(rows["BW-002"]["earliestStartHour"], 5)
        self.assertEqual(rows["BW-002"]["earliestFinishHour"], 6)
        self.assertEqual(rows["BW-002"]["requiredGateEvidenceCompleteHours"], {"BG-001": 5})
        gate = schedule["gateEvidenceMilestones"][0]
        self.assertEqual(gate["hypotheticalEvidenceCompleteHour"], 5)
        self.assertFalse(gate["gateAcceptancePerformed"])
        self.assertEqual(gate["status"], "UNRESOLVED")
        self.assertEqual(schedule["topologicalOrder"], ["BW-001", "BW-002"])

    def test_default_gate_evidence_times_and_package_preconditions(self):
        schedule = calculate_schedule(self.registers)
        gates = {gate["gateId"]: gate for gate in schedule["gateEvidenceMilestones"]}
        expected = {
            "BG-001": 16, "BG-002": 40, "BG-003": 56, "BG-004": 80,
            "BG-005": 176, "BG-006": 176, "BG-007": 80, "BG-008": 320,
            "BG-009": 320, "BG-010": 352, "BG-011": 376, "BG-012": 408,
            "BG-013": 472, "BG-014": 472, "BG-015": 472,
        }
        self.assertEqual({key: value["hypotheticalEvidenceCompleteHour"] for key, value in gates.items()}, expected)
        self.assertTrue(all(not gate["gateAcceptancePerformed"] for gate in gates.values()))
        for package in schedule["packages"]:
            for gate_id in package["requiredGateIds"]:
                self.assertGreaterEqual(package["earliestStartHour"], gates[gate_id]["hypotheticalEvidenceCompleteHour"])
        self.assertEqual(schedule["syntheticDurationHours"], 472)

    def test_package_requiring_its_own_output_gate_is_cycle(self):
        def mutate(rows):
            rows[0]["requiredGateIds"] = "BG-001"
        work = self.copy_register("work-breakdown.csv", mutate)
        with self.assertRaisesRegex(ConfigError, "package/gate dependency cycle"):
            self.registers_with_work(work)

    def test_indirect_package_gate_cycle_is_detected(self):
        registers = BunkerRegisters(
            (
                self.custom_package("BW-001", 1, dependencies=("BW-002",)),
                self.custom_package("BW-002", 1, gate_ids=("BG-001",)),
            ),
            (self.custom_gate("BG-001", ("BW-001",)),),
            (),
        )
        with self.assertRaisesRegex(ConfigError, "package/gate dependency cycle"):
            calculate_schedule(registers)

    def test_independent_cpm_branch_and_gate_evidence_use_maximum(self):
        registers = BunkerRegisters(
            (
                self.custom_package("BW-001", 5),
                self.custom_package("BW-002", 2),
                self.custom_package("BW-003", 1, dependencies=("BW-001", "BW-002"), gate_ids=("BG-001",)),
            ),
            (self.custom_gate("BG-001", ("BW-002",)),),
            (),
        )
        schedule = calculate_schedule(registers)
        rows = {row["packageId"]: row for row in schedule["packages"]}
        self.assertEqual(rows["BW-003"]["earliestStartHour"], 5)
        self.assertEqual(schedule["syntheticDurationHours"], 6)
        self.assertEqual(schedule["criticalPathPackageIds"], ["BW-001", "BW-003"])
        self.assertEqual(schedule["gateEvidenceMilestones"][0]["hypotheticalEvidenceCompleteHour"], 2)

    def test_disconnected_terminal_positive_half_nanosecond_hour_slack_is_not_zero(self):
        registers = BunkerRegisters(
            (self.custom_package("BW-001", 1 - 5e-10), self.custom_package("BW-002", 1)),
            (),
            (),
        )
        schedule = calculate_schedule(registers)
        self.assertEqual(schedule["allZeroSlackPackageIds"], ["BW-002"])
        self.assertEqual(schedule["criticalPathPackageIds"], ["BW-002"])

    def test_binding_path_ignores_predecessor_with_small_positive_slack(self):
        registers = BunkerRegisters(
            (
                self.custom_package("BW-001", 1),
                self.custom_package("BW-002", 1 - 5e-10),
                self.custom_package("BW-003", 1, dependencies=("BW-001", "BW-002")),
            ),
            (),
            (),
        )
        schedule = calculate_schedule(registers)
        self.assertEqual(schedule["allZeroSlackPackageIds"], ["BW-001", "BW-003"])
        self.assertEqual(schedule["criticalPathPackageIds"], ["BW-001", "BW-003"])

    def test_positive_product_underflow_is_rejected(self):
        for key in self.data["geometry"]:
            if key != "provenance":
                self.data["geometry"][key] = 1e-200
        with self.assertRaisesRegex(ConfigError, "underflowed nonzero external footprint"):
            calculate_quantities(parse_bunker_input(self.data))

    def test_positive_wall_geometry_cannot_cancel_to_zero(self):
        self.data["geometry"]["wallThickness_m"] = 1e-200
        with self.assertRaisesRegex(ConfigError, "positive wall geometry collapsed"):
            calculate_quantities(parse_bunker_input(self.data))

    def test_positive_backfill_cannot_cancel_to_zero(self):
        self.data["geometry"]["workingSpace_m"] = 0
        self.data["geometry"]["drainageLayer_m"] = 0
        self.data["geometry"]["roofCover_m"] = 1e-200
        with self.assertRaisesRegex(ConfigError, "positive backfill geometry collapsed"):
            calculate_quantities(parse_bunker_input(self.data))

    def test_tiny_geometry_division_underflow_is_rejected(self):
        for key in self.data["geometry"]:
            if key != "provenance":
                self.data["geometry"][key] = 1e-100
        self.data["soilModel"]["compactedToInSituRatio"] = 1e308
        with self.assertRaisesRegex(ConfigError, "underflowed nonzero in-situ equivalent backfill"):
            calculate_quantities(parse_bunker_input(self.data))

    def write_site(self, data):
        path = self.temp_path / "site.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_site_rejects_unknown_top_level_and_missing_privacy_fields(self):
        original = json.loads((ROOT / "projects/bunker01/site-inputs.json").read_text(encoding="utf-8"))
        for key in ("locationPrivacy", "provenance"):
            with self.subTest(missing=key):
                data = copy.deepcopy(original)
                data.pop(key)
                with self.assertRaisesRegex(ConfigError, "missing fields"):
                    load_bunker_site(self.write_site(data))
        original["unexpectedPrivateCoordinate"] = "not allowed"
        with self.assertRaisesRegex(ConfigError, "unknown fields: unexpectedPrivateCoordinate"):
            load_bunker_site(self.write_site(original))

    def test_site_rejects_nested_extras_and_missing_explicit_nulls(self):
        original = json.loads((ROOT / "projects/bunker01/site-inputs.json").read_text(encoding="utf-8"))
        for key in ("value", "evidenceReference"):
            with self.subTest(missing=key):
                data = copy.deepcopy(original)
                data["requiredInputs"]["legalLocation"].pop(key)
                with self.assertRaisesRegex(ConfigError, "missing fields"):
                    load_bunker_site(self.write_site(data))
        original["requiredInputs"]["legalLocation"]["unexpectedPrivateCoordinate"] = None
        with self.assertRaisesRegex(ConfigError, "unknown fields: unexpectedPrivateCoordinate"):
            load_bunker_site(self.write_site(original))

    def test_xml_illegal_register_control_character_is_rejected(self):
        def mutate(rows):
            rows[0]["name"] = "Bad \x01 package"
        work = self.copy_register("work-breakdown.csv", mutate)
        with self.assertRaisesRegex(ConfigError, "XML-illegal"):
            load_work_breakdown(work)

    def test_json_control_and_unpaired_surrogate_are_rejected(self):
        for value in ("Bad \x01 notice", "Bad \ud800 notice"):
            with self.subTest(value=value):
                self.data["syntheticNotice"] = value
                with self.assertRaisesRegex(ConfigError, "XML-illegal"):
                    parse_bunker_input(self.data)

    def test_svg_dynamic_columns_banner_and_footer_do_not_overlap(self):
        svg = schedule_svg(self.result())
        root = ET.fromstring(svg)
        ns = {"s": "http://www.w3.org/2000/svg"}
        width = float(root.attrib["width"])
        banner = root.find("s:rect[@data-role='banner']", ns)
        self.assertEqual(float(banner.attrib["width"]), width - 30)
        labels = {node.attrib["data-package-id"]: node for node in root.findall("s:text[@data-role='package-label']", ns)}
        names = {node.attrib["data-package-id"]: node for node in root.findall("s:text[@data-role='package-name']", ns)}
        grid_x = min(float(node.attrib["x1"]) for node in root.findall("s:line[@data-role='timeline-grid']", ns))
        for package_id, label in labels.items():
            label_text = "".join(label.itertext())
            name_spans = list(names[package_id])
            self.assertTrue(name_spans)
            for span in name_spans:
                self.assertGreaterEqual(float(span.attrib["x"]), 25 + len(label_text) * 8)
                self.assertLessEqual(float(span.attrib["x"]) + len("".join(span.itertext())) * 7, grid_x - 30)
        self.assertIn("BW-008", labels)
        self.assertIn("future_supervised_autonomy", "".join(labels["BW-008"].itertext()))
        footer = "".join(root.findall("s:text", ns)[-1].itertext())
        self.assertNotIn("BW-001 →", footer)
        self.assertIn("see result.json", footer)
        ET.fromstring(svg)

    def test_svg_long_unicode_custom_text_wraps_without_invalid_layout(self):
        def mutate(rows):
            rows[0]["name"] = "⚙ " + "long-name-" * 40 + "<>&\""
        work = self.copy_register("work-breakdown.csv", mutate)
        svg = schedule_svg(plan_bunker(self.model, self.registers_with_work(work), self.site))
        root = ET.fromstring(svg)
        ns = {"s": "http://www.w3.org/2000/svg"}
        name = root.find("s:text[@data-role='package-name'][@data-package-id='BW-001']", ns)
        self.assertGreater(len(list(name)), 5)
        self.assertGreater(float(root.attrib["height"]), float(ET.fromstring(schedule_svg(self.result())).attrib["height"]))
        self.assertEqual(svg, schedule_svg(plan_bunker(self.model, self.registers_with_work(work), self.site)))

    def test_static_openscad_scan_covers_all_four_sources(self):
        self.assertIn("4 sources passed static delimiter checks", static_openscad_check())

    def run_cli(self, *args):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run([sys.executable, "-m", "open_construction_equipment", *map(str, args)], cwd=ROOT, env=env, text=True, capture_output=True, timeout=30, check=False)

    def test_cli_success_writes_matching_json_and_svg(self):
        output = self.temp_path / "cli"
        completed = self.run_cli("bunker", "--output-dir", output, "--json")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["schedule"]["syntheticDurationHours"], 472)
        self.assertEqual((output / "result.json").read_text(encoding="utf-8"), completed.stdout)
        self.assertTrue((output / "schedule.svg").is_file())

    def test_cli_invalid_input_and_missing_register_are_controlled(self):
        bad = self.write_input({}, "bad.json")
        for args in (("bunker", "--input", bad), ("bunker", "--work-breakdown", self.temp_path / "missing.csv")):
            with self.subTest(args=args):
                completed = self.run_cli(*args, "--output-dir", self.temp_path / "not-written", "--json")
                self.assertEqual(completed.returncode, 2)
                self.assertIn("ERROR:", completed.stderr)
                self.assertNotIn("Traceback", completed.stderr)

    def test_cli_huge_integer_is_controlled_without_output(self):
        self.data["geometry"]["roofCover_m"] = 10**400
        path = self.write_input(self.data, "huge.json")
        output = self.temp_path / "huge-output"
        completed = self.run_cli("bunker", "--input", path, "--output-dir", output)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("finite number", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)
        self.assertFalse(output.exists())

    def test_schema_and_runtime_strictness_agree(self):
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), set(self.data))
        self.assertEqual(set(schema["properties"]), set(self.data))
        for section in ("geometry", "soilModel", "wasteModel"):
            self.assertFalse(schema["properties"][section]["additionalProperties"])
            self.assertEqual(set(schema["properties"][section]["required"]), set(self.data[section]))
        provenance = schema["$defs"]["provenance"]
        self.assertEqual(schema["$defs"]["nonEmptyString"]["pattern"], r"\S")
        self.data["unknown"] = True
        with self.assertRaisesRegex(ConfigError, "unknown fields"):
            parse_bunker_input(self.data)

    @unittest.skipUnless(importlib.util.find_spec("jsonschema"), "optional jsonschema package unavailable")
    def test_optional_jsonschema_validation_matches_runtime(self):
        import jsonschema
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(json.loads(INPUT.read_text(encoding="utf-8")))
        invalid = copy.deepcopy(self.data)
        invalid["geometry"]["roofCover_m"] = -1
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(invalid)
        with self.assertRaises(ConfigError):
            parse_bunker_input(invalid)

    def test_source_validation_covers_bunker_and_cad(self):
        report = validate_repository(ROOT)
        self.assertEqual(report["status"], "passed", report["errors"])
        self.assertEqual(report["validationScope"], "source-repository")
        self.assertTrue(report["bunkerCadGeometryChecked"])
        self.assertEqual(report["bunkerWorkPackagesChecked"], 22)
        self.assertEqual(report["bunkerGatesChecked"], 15)
        self.assertEqual(report["bunkerFleetEntriesChecked"], 8)

    def test_cad_geometry_mismatch_is_rejected(self):
        cad = self.temp_path / "projects/bunker01/cad/parameters.scad"
        text = (ROOT / "projects/bunker01/cad/parameters.scad").read_text(encoding="utf-8").replace("internal_length = 4000", "internal_length = 4001")
        cad.parent.mkdir(parents=True)
        cad.write_text(text, encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "does not match CAD"):
            validate_bunker_cad_geometry(self.temp_path, self.model)

    def test_wheel_metadata_contains_canonical_bunker_resources_without_copies(self):
        import tomllib
        with (ROOT / "pyproject.toml").open("rb") as handle:
            project = tomllib.load(handle)
        self.assertEqual(project["project"]["version"], "0.5.0")
        data_files = project["tool"]["setuptools"]["data-files"]
        prefix = "share/open-construction-equipment/"
        self.assertEqual(data_files[prefix + "examples/bunker"], ["examples/bunker/synthetic-bunker01.json"])
        self.assertEqual(data_files[prefix + "projects/bunker01"], ["projects/bunker01/site-inputs.json"])
        self.assertEqual(len(data_files[prefix + "projects/bunker01/construction"]), 3)


if __name__ == "__main__":
    unittest.main()
