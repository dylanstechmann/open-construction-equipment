# SPDX-License-Identifier: Apache-2.0
import copy
from dataclasses import FrozenInstanceError, replace
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest

from open_construction_equipment.config import ConfigError
from open_construction_equipment.economics import (
    AcquisitionPathway,
    CostCategory,
    CostLine,
    EconomicsResult,
    EvidenceStatus,
    PathwayCost,
    PathwayEvaluator,
    RentalBillingUnit,
    RentalItem,
    break_even,
    compare_pathways,
    economics_result_json,
    evaluate_pathway,
    fabrication_totals,
    load_economics_input,
    parse_economics_input,
    rental_cost,
    write_economics_result,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_PATH = ROOT / "examples/economics/synthetic-pathways.json"
SCHEMA_PATH = ROOT / "schemas/economics-input.schema.json"


def policy_for(model, pathway):
    return next(policy for policy in model.policies if policy.pathway is pathway)


def line_for(cost, category):
    return next(line for line in cost.lines if line.category is category)


def affine_cost(pathway, fixed, variable, hours=0.0):
    amount = fixed + variable * hours
    return PathwayCost(
        pathway=pathway,
        operating_hours=hours,
        currency="USD",
        lines=(CostLine(CostCategory.WEAR_MAINTENANCE, fixed, variable, "Synthetic affine test line."),),
        shop_startup_tooling_capex=0.0,
        fabrication_cost=0.0,
        labor_hours=0.0,
        labor_cost=0.0,
        rental_cost=0.0,
        wear_maintenance_cost=amount,
        energy_cost=0.0,
        site_adaptation_cost=0.0,
        total_cost=amount,
    )


class ExampleAccountingTests(unittest.TestCase):
    def setUp(self):
        self.model = load_economics_input(EXAMPLE_PATH)

    def evaluate(self, pathway, hours):
        return evaluate_pathway(self.model, policy_for(self.model, pathway), hours)

    def test_fabrication_totals_and_named_labor_role(self):
        self.assertEqual(
            fabrication_totals(self.model, AcquisitionPathway.DIY),
            (12000.0, 4000.0, 120.0, 7500.0),
        )
        self.assertEqual(
            fabrication_totals(self.model, AcquisitionPathway.HYBRID),
            (3000.0, 1000.0, 40.0, 1500.0),
        )
        self.assertEqual(fabrication_totals(self.model, AcquisitionPathway.RENTAL), (0.0, 0.0, 0.0, 0.0))
        diy = self.evaluate(AcquisitionPathway.DIY, 0)
        self.assertEqual(diy.labor_cost, 5400.0)
        self.assertEqual(diy.labor_hours, 120.0)

    def test_zero_hour_fixed_costs_and_zero_variable_costs(self):
        expected = {
            AcquisitionPathway.DIY: 30000.0,
            AcquisitionPathway.RENTAL: 3000.0,
            AcquisitionPathway.HYBRID: 8500.0,
        }
        for pathway, fixed in expected.items():
            with self.subTest(pathway=pathway):
                cost = self.evaluate(pathway, 0)
                self.assertEqual(cost.total_cost, fixed)
                self.assertEqual(cost.rental_cost, 0.0)
                self.assertEqual(cost.wear_maintenance_cost, 0.0)
                self.assertEqual(cost.energy_cost, 0.0)
                self.assertEqual(line_for(cost, CostCategory.RENTAL).variable_cost_per_h >= 0, True)
        self.assertEqual(line_for(self.evaluate(AcquisitionPathway.RENTAL, 0), CostCategory.MOBILIZATION).fixed_cost, 1600)

    def test_diy_line_item_totals_and_fixed_ownership_allocation(self):
        cost = self.evaluate(AcquisitionPathway.DIY, 80)
        self.assertEqual(cost.shop_startup_tooling_capex, 7500)
        self.assertEqual(cost.fabrication_cost, 16000)
        self.assertEqual(cost.labor_cost, 5400)
        self.assertEqual(cost.site_adaptation_cost, 1100)
        self.assertEqual(cost.wear_maintenance_cost, 1060)
        self.assertEqual(cost.energy_cost, 480)
        self.assertEqual(cost.total_cost, 31540)
        # 4 ownership + (0.5 + 6000/1200) + (0.25 + 1500/750) + 1.5 fabrication wear.
        self.assertEqual(line_for(cost, CostCategory.WEAR_MAINTENANCE).variable_cost_per_h, 13.25)
        self.assertEqual(cost.total_cost, sum(
            line.fixed_cost + line.variable_cost_per_h * cost.operating_hours for line in cost.lines
        ))

    def test_rental_and_hybrid_hand_totals(self):
        rental = self.evaluate(AcquisitionPathway.RENTAL, 100)
        self.assertEqual(rental.rental_cost, 18175)
        self.assertEqual(rental.energy_cost, 1700)
        self.assertEqual(rental.wear_maintenance_cost, 50)
        self.assertEqual(rental.total_cost, 22925)
        hybrid = self.evaluate(AcquisitionPathway.HYBRID, 100)
        self.assertEqual(hybrid.shop_startup_tooling_capex, 1500)
        self.assertEqual(hybrid.fabrication_cost, 4000)
        self.assertEqual(hybrid.labor_cost, 1800)
        self.assertEqual(hybrid.rental_cost, 8500)
        self.assertEqual(hybrid.energy_cost, 1300)
        self.assertEqual(hybrid.wear_maintenance_cost, 725)
        self.assertEqual(hybrid.total_cost, 19025)

    def test_only_selected_tooling_and_items_contribute(self):
        hybrid = self.evaluate(AcquisitionPathway.HYBRID, 10)
        self.assertEqual(hybrid.shop_startup_tooling_capex, 1500)
        self.assertNotEqual(hybrid.shop_startup_tooling_capex, 7500)
        self.assertEqual(hybrid.labor_hours, 40)
        self.assertEqual(line_for(hybrid, CostCategory.MOBILIZATION).fixed_cost, 800)

    def test_included_and_separate_rental_wear_are_not_double_counted(self):
        rental = self.evaluate(AcquisitionPathway.RENTAL, 80)
        # Only rental-week's explicitly separate 0.5/hour is charged.
        self.assertEqual(rental.wear_maintenance_cost, 40)
        hybrid = self.evaluate(AcquisitionPathway.HYBRID, 80)
        # Hybrid: 4 ownership + 2.25 tooling + 0.5 fabrication + 0.5 rental-week.
        self.assertEqual(line_for(hybrid, CostCategory.WEAR_MAINTENANCE).variable_cost_per_h, 7.25)

    def test_site_adaptation_deltas_are_selected_and_signed(self):
        model = replace(
            self.model,
            site_adaptations=tuple(
                replace(item, cost_delta=-100.0) if item.adaptation_id == "SA-ECON-HYBRID" else item
                for item in self.model.site_adaptations
            ),
        )
        cost = evaluate_pathway(model, policy_for(model, AcquisitionPathway.HYBRID), 0)
        self.assertEqual(cost.site_adaptation_cost, -100)
        self.assertEqual(cost.total_cost, 8000)

    def test_negative_adapted_total_is_rejected_not_clamped(self):
        model = replace(
            self.model,
            site_adaptations=tuple(
                replace(item, cost_delta=-40000.0) if item.adaptation_id == "SA-ECON-DIY" else item
                for item in self.model.site_adaptations
            ),
        )
        with self.assertRaisesRegex(ConfigError, "negative adapted"):
            evaluate_pathway(model, policy_for(model, AcquisitionPathway.DIY), 0)

    def test_all_result_flags_and_currencies_remain_blocked(self):
        result = compare_pathways(self.model)
        self.assertIs(result.status, EvidenceStatus.SIMULATED_UNREVIEWED)
        self.assertFalse(result.quotes_obtained)
        self.assertFalse(result.procurement_authorized)
        self.assertFalse(result.physical_validation_performed)
        self.assertTrue(all(cost.currency == "USD" for cost in result.pathway_costs))


class RentalProrationTests(unittest.TestCase):
    def item(self, unit, rate):
        return RentalItem(
            "rental-test", unit, rate, 125.0, 2, 7.0, 0.0, True,
            (AcquisitionPathway.RENTAL,),
        )

    def test_hour_day_and_week_proration(self):
        expected = (
            (RentalBillingUnit.HOUR, 12.0, 120.0),
            (RentalBillingUnit.DAY_8H, 96.0, 120.0),
            (RentalBillingUnit.WEEK_40H, 400.0, 100.0),
        )
        for unit, rate, amount in expected:
            with self.subTest(unit=unit):
                self.assertEqual(rental_cost(self.item(unit, rate), 10), (amount, 250.0, 70.0))

    def test_zero_and_negative_hours(self):
        self.assertEqual(rental_cost(self.item(RentalBillingUnit.DAY_8H, 96), 0), (0, 250, 0))
        with self.assertRaises(ConfigError):
            rental_cost(self.item(RentalBillingUnit.HOUR, 12), -1)

    def test_included_wear_requires_zero_reserve(self):
        with self.assertRaises(ConfigError):
            rental_cost(replace(self.item(RentalBillingUnit.HOUR, 12), hourly_wear_reserve=1), 1)

    def test_nonfinite_overflow_is_controlled(self):
        with self.assertRaises(ConfigError):
            rental_cost(self.item(RentalBillingUnit.HOUR, 1e308), 1e308)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
        self.model = parse_economics_input(copy.deepcopy(self.data))

    def parse_with(self, change):
        data = copy.deepcopy(self.data)
        change(data)
        return parse_economics_input(data)

    def test_evaluation_hours_are_sorted_and_duplicates_fail(self):
        model = self.parse_with(lambda data: data.update(evaluationHours_h=[600, 0, 250, 80, 1200]))
        self.assertEqual(model.evaluation_hours, (0, 80, 250, 600, 1200))
        with self.assertRaisesRegex(ConfigError, "unique"):
            self.parse_with(lambda data: data.update(evaluationHours_h=[0, 80, 80]))

    def test_labor_limit_is_enforced_for_each_owned_policy(self):
        with self.assertRaisesRegex(ConfigError, "exceed available_hours"):
            self.parse_with(lambda data: data["laborRates"][0].update(availableHours_h=119))
        model = replace(
            self.model,
            labor_rates=(replace(self.model.labor_rates[0], available_hours=39), self.model.labor_rates[1]),
        )
        with self.assertRaisesRegex(ConfigError, "exceed available_hours"):
            evaluate_pathway(model, policy_for(model, AcquisitionPathway.HYBRID), 0)

    def test_missing_role_and_duplicate_roles_fail(self):
        with self.assertRaisesRegex(ConfigError, "exactly one labor rate"):
            self.parse_with(lambda data: data.update(fabricationLaborRole="unknown"))
        with self.assertRaisesRegex(ConfigError, "labor roles"):
            self.parse_with(lambda data: data["laborRates"][1].update(role="fabricator"))

    def test_diy_rental_and_hybrid_policy_constraints(self):
        with self.assertRaisesRegex(ConfigError, "DIY cannot"):
            self.parse_with(lambda data: data["policies"][0].update(rentalItemIds=["rental-hour"]))
        with self.assertRaisesRegex(ConfigError, "RENTAL cannot"):
            self.parse_with(lambda data: data["policies"][1].update(ownedItemIds=["tool-welder"]))
        with self.assertRaisesRegex(ConfigError, "HYBRID requires"):
            self.parse_with(lambda data: data["policies"][2].update(rentalItemIds=[]))
        with self.assertRaisesRegex(ConfigError, "HYBRID requires"):
            self.parse_with(lambda data: data["policies"][2].update(ownedItemIds=[]))

    def test_unknown_duplicate_and_unauthorized_references_fail(self):
        with self.assertRaisesRegex(ConfigError, "unknown item"):
            self.parse_with(lambda data: data["policies"][0].update(ownedItemIds=["not-priced"]))
        with self.assertRaisesRegex(ConfigError, "unique IDs"):
            self.parse_with(lambda data: data["policies"][0]["ownedItemIds"].append("tool-welder"))
        with self.assertRaisesRegex(ConfigError, "applies_to"):
            self.parse_with(lambda data: data["policies"][2]["ownedItemIds"].append("fab-chassis"))
        with self.assertRaisesRegex(ConfigError, "unknown item"):
            self.parse_with(lambda data: data["policies"][0].update(siteAdaptationIds=["SA-MISSING"]))

    def test_duplicate_items_policies_and_adaptations_fail(self):
        with self.assertRaisesRegex(ConfigError, "owned item IDs"):
            self.parse_with(lambda data: data["fabrication"].append(copy.deepcopy(data["fabrication"][0])))
        with self.assertRaisesRegex(ConfigError, "exactly DIY"):
            self.parse_with(lambda data: data["policies"].append(copy.deepcopy(data["policies"][0])))
        with self.assertRaisesRegex(ConfigError, "site adaptation IDs"):
            self.parse_with(lambda data: data["siteAdaptations"].append(copy.deepcopy(data["siteAdaptations"][0])))

    def test_currency_mismatch_and_shape_fail(self):
        with self.assertRaisesRegex(ConfigError, "currency"):
            self.parse_with(lambda data: data["siteAdaptations"][0].update(currency="EUR"))
        with self.assertRaisesRegex(ConfigError, r"\[A-Z\]\{3\}"):
            self.parse_with(lambda data: data.update(currency="usd"))

    def test_strict_unknown_missing_boolean_and_provenance_fields(self):
        with self.assertRaisesRegex(ConfigError, "unknown fields"):
            self.parse_with(lambda data: data.update(unpricedMystery=0))
        with self.assertRaisesRegex(ConfigError, "missing fields"):
            self.parse_with(lambda data: data.pop("annualFixedOwnershipCost"))
        with self.assertRaisesRegex(ConfigError, "finite number"):
            self.parse_with(lambda data: data.update(annualFixedOwnershipCost=True))
        with self.assertRaisesRegex(ConfigError, "non-empty"):
            self.parse_with(lambda data: data.update(analysisId="   "))
        with self.assertRaises(ConfigError):
            self.parse_with(lambda data: data["provenance"].update(ownerSupplied=True))

    def test_included_wear_and_integer_mobilization_parse_checks(self):
        with self.assertRaisesRegex(ConfigError, "included wear"):
            self.parse_with(lambda data: data["rentals"][0].update(hourlyWearReserve=1))
        with self.assertRaisesRegex(ConfigError, "integer"):
            self.parse_with(lambda data: data["rentals"][0].update(mobilizationsPerProject=1.5))
        with self.assertRaisesRegex(ConfigError, "integer"):
            self.parse_with(lambda data: data["rentals"][0].update(mobilizationsPerProject=True))

    def test_immutable_frozen_models(self):
        with self.assertRaises(FrozenInstanceError):
            self.model.currency = "EUR"


class BreakEvenTests(unittest.TestCase):
    def test_positive_crossing_and_cheaper_side_labels(self):
        result = break_even(
            affine_cost(AcquisitionPathway.DIY, 1000, 10),
            affine_cost(AcquisitionPathway.RENTAL, 0, 20),
        )
        self.assertEqual(result.operating_hours, 100)
        self.assertIs(result.lower_cost_path_below, AcquisitionPathway.RENTAL)
        self.assertIs(result.lower_cost_path_above, AcquisitionPathway.DIY)
        self.assertFalse(result.is_exact_tie_everywhere)

    def test_equal_slope_identifies_cheaper_everywhere(self):
        result = break_even(
            affine_cost(AcquisitionPathway.DIY, 100, 10),
            affine_cost(AcquisitionPathway.RENTAL, 200, 10),
        )
        self.assertIsNone(result.operating_hours)
        self.assertIs(result.lower_cost_path_below, AcquisitionPathway.DIY)
        self.assertIs(result.lower_cost_path_above, AcquisitionPathway.DIY)

    def test_exact_tie_everywhere(self):
        result = break_even(
            affine_cost(AcquisitionPathway.DIY, 100, 10),
            affine_cost(AcquisitionPathway.RENTAL, 100, 10),
        )
        self.assertTrue(result.is_exact_tie_everywhere)
        self.assertIsNone(result.operating_hours)
        self.assertIsNone(result.lower_cost_path_below)
        self.assertIsNone(result.lower_cost_path_above)

    def test_negative_candidate_has_no_positive_crossing(self):
        result = break_even(
            affine_cost(AcquisitionPathway.DIY, 0, 10),
            affine_cost(AcquisitionPathway.RENTAL, 1000, 20),
        )
        self.assertIsNone(result.operating_hours)
        self.assertIs(result.lower_cost_path_below, AcquisitionPathway.DIY)
        self.assertIs(result.lower_cost_path_above, AcquisitionPathway.DIY)
        self.assertIn("not at positive", result.reason)

    def test_fixed_cost_equality_is_zero_crossing_not_positive(self):
        result = break_even(
            affine_cost(AcquisitionPathway.DIY, 100, 10),
            affine_cost(AcquisitionPathway.RENTAL, 100, 20),
        )
        self.assertIsNone(result.operating_hours)
        self.assertIsNone(result.lower_cost_path_below)
        self.assertIs(result.lower_cost_path_above, AcquisitionPathway.DIY)

    def test_mismatched_hours_currency_and_path_fail(self):
        with self.assertRaises(ConfigError):
            break_even(affine_cost(AcquisitionPathway.DIY, 0, 1, 0), affine_cost(AcquisitionPathway.RENTAL, 0, 2, 1))
        with self.assertRaises(ConfigError):
            break_even(
                affine_cost(AcquisitionPathway.DIY, 0, 1),
                replace(affine_cost(AcquisitionPathway.RENTAL, 0, 2), currency="EUR"),
            )
        with self.assertRaises(ConfigError):
            break_even(affine_cost(AcquisitionPathway.DIY, 0, 1), affine_cost(AcquisitionPathway.DIY, 0, 2))

    def test_example_pairings_and_exact_crossing_totals(self):
        model = load_economics_input(EXAMPLE_PATH)
        result = compare_pathways(model)
        crossings = {(item.left_path, item.right_path): item for item in result.break_even}
        diy_rental = crossings[(AcquisitionPathway.DIY, AcquisitionPathway.RENTAL)]
        diy_hybrid = crossings[(AcquisitionPathway.DIY, AcquisitionPathway.HYBRID)]
        rental_hybrid = crossings[(AcquisitionPathway.RENTAL, AcquisitionPathway.HYBRID)]
        self.assertEqual(diy_rental.operating_hours, 150)
        self.assertEqual(diy_hybrid.operating_hours, 250)
        self.assertAlmostEqual(rental_hybrid.operating_hours, 5500 / 94)
        for (left, right), crossing in crossings.items():
            with self.subTest(left=left, right=right):
                left_cost = evaluate_pathway(model, policy_for(model, left), crossing.operating_hours)
                right_cost = evaluate_pathway(model, policy_for(model, right), crossing.operating_hours)
                self.assertAlmostEqual(left_cost.total_cost, right_cost.total_cost, places=6)


class ResultTests(unittest.TestCase):
    def setUp(self):
        self.model = load_economics_input(EXAMPLE_PATH)
        self.result = compare_pathways(self.model)

    def test_canonical_order_and_unique_horizons(self):
        expected = [
            (pathway, hours)
            for pathway in (AcquisitionPathway.DIY, AcquisitionPathway.RENTAL, AcquisitionPathway.HYBRID)
            for hours in (0, 80, 250, 600, 1200)
        ]
        self.assertEqual([(cost.pathway, cost.operating_hours) for cost in self.result.pathway_costs], expected)
        self.assertEqual(len(self.result.break_even), 3)

    def test_facade_and_byte_serialization_are_deterministic(self):
        repeated = PathwayEvaluator().run(self.model)
        self.assertEqual(economics_result_json(self.result), economics_result_json(repeated))
        self.assertEqual(economics_result_json(self.result), economics_result_json(compare_pathways(self.model)))
        parsed = json.loads(economics_result_json(self.result))
        self.assertEqual(parsed["status"], "SIMULATED_UNREVIEWED")
        self.assertFalse(parsed["quotesObtained"])
        self.assertFalse(parsed["procurementAuthorized"])
        self.assertFalse(parsed["physicalValidationPerformed"])
        self.assertEqual(parsed["pathwayCosts"][0]["totalCost"], 30000)

    def test_writer_matches_stdout_and_creates_only_result(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "nested" / "economics"
            path = write_economics_result(self.result, destination)
            self.assertEqual(path, destination / "result.json")
            self.assertEqual(path.read_text(encoding="utf-8"), economics_result_json(self.result))
            self.assertEqual(tuple(destination.iterdir()), (path,))

    def test_serialization_rejects_tampered_totals_and_flags(self):
        with self.assertRaisesRegex(ConfigError, "does not reconcile"):
            economics_result_json(replace(self.result, pathway_costs=(replace(
                self.result.pathway_costs[0], total_cost=1,
            ), *self.result.pathway_costs[1:])))
        with self.assertRaisesRegex(ConfigError, "must remain false"):
            economics_result_json(replace(self.result, procurement_authorized=True))
        with self.assertRaisesRegex(ConfigError, "currency"):
            economics_result_json(replace(self.result, pathway_costs=(replace(
                self.result.pathway_costs[0], currency="EUR",
            ), *self.result.pathway_costs[1:])))


@unittest.skipUnless(importlib.util.find_spec("jsonschema"), "optional jsonschema is not installed")
class OptionalSchemaTests(unittest.TestCase):
    def test_schema_is_valid_and_accepts_canonical_example(self):
        from jsonschema import Draft202012Validator

        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        data = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(list(validator.iter_errors(data)), [])

    def test_schema_rejects_invalid_envelopes(self):
        from jsonschema import Draft202012Validator

        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        data = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
        data["analysisId"] = "  "
        data["unexpected"] = True
        self.assertTrue(list(validator.iter_errors(data)))
        data = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
        data["policies"][0]["rentalItemIds"] = ["rental-hour"]
        self.assertTrue(list(validator.iter_errors(data)))


if __name__ == "__main__":
    unittest.main()
