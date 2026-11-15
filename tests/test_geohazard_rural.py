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
from open_construction_equipment.geohazard_rural import (
    AdaptationKind,
    ConstructionStrategy,
    FoundationStrategy,
    LocalFeature,
    LocalPoint,
    PermitFinding,
    RiskLevel,
    ScreeningDecision,
    SiteAdvisor,
    adapt_to_existing_site,
    assess_permits,
    assess_risks,
    geohazard_result_json,
    load_geohazard_document,
    load_geohazard_input,
    minimum_feature_distance,
    parse_geohazard_input,
    reject_private_location_data,
    screen_candidate_parcels,
    write_geohazard_result,
)

ROOT = Path(__file__).resolve().parents[1]
SCREEN_PATH = ROOT / "examples/geohazard/synthetic-screen.json"
ADAPT_PATH = ROOT / "examples/geohazard/synthetic-adapt.json"
SCHEMA_PATH = ROOT / "schemas/geohazard-rural.schema.json"


def risk_by_name(factors):
    return {risk.domain: risk for risk in assess_risks(factors)}


class PrivacyTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(SCREEN_PATH.read_text(encoding="utf-8"))

    def test_forbidden_keys_fail_at_top_nested_and_list_positions(self):
        forbidden = [
            "latitude", "longitude", "GPS", "streetAddress", "parcelId", "APN", "geohash",
            "legalLocation", "plusCode", "postcode", "taxId", "realPropertyId", "gnss", "deed",
        ]
        for key in forbidden:
            for location in ("top", "nested", "list"):
                with self.subTest(key=key, location=location):
                    data = copy.deepcopy(self.data)
                    if location == "top":
                        data[key] = "redacted"
                    elif location == "nested":
                        data["candidates"][0]["factors"]["karst"][key] = "redacted"
                    else:
                        data["candidates"][0]["factors"]["features"].append({key: "redacted"})
                    with self.assertRaises(ConfigError):
                        parse_geohazard_input(data)

    def test_coordinate_geocode_url_and_address_text_fails(self):
        values = [
            "lat: 40.7128, lon: -74.0060", "latitude=-33.8", "GPS 40.7 -74.0",
            "40.7128, -74.0060", "40.7 N, 74.0 W", "https://example.invalid/map?lat=40&lon=-74",
            "https://example.invalid/map?q=40.7%2C-74.0", "123 Main Street", "PO Box 42",
            "849VCWC8+R9", "geohash dr5regw", "geohash", "https://example.invalid/map?q=40.7,-74.0",
        ]
        for value in values:
            with self.subTest(value=value):
                data = copy.deepcopy(self.data)
                data["analysisId"] = value
                with self.assertRaises(ConfigError):
                    parse_geohazard_input(data)

    def test_relative_points_labels_and_token_boundaries_are_accepted(self):
        reject_private_location_data({"translation_m": -120.5, "point": {"x_m": -120.5, "y_m": 45.2}})
        parcels = parse_geohazard_input(copy.deepcopy(self.data))
        self.assertEqual(parcels[0].anonymous_label, "CANDIDATE-A")
        self.assertEqual(parcels[0].factors.features[0].vertices_local_m[0].x_m, 60)
        data = copy.deepcopy(self.data)
        data["translation_m"] = 12
        with self.assertRaisesRegex(ConfigError, "unknown fields"):
            parse_geohazard_input(data)

    def test_source_privacy_failure_occurs_before_output_creation(self):
        self.data["candidates"][0]["factors"]["privacy"]["longitude"] = -74.0
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "input.json"
            output = Path(temp) / "output"
            source.write_text(json.dumps(self.data), encoding="utf-8")
            with self.assertRaises(ConfigError):
                write_geohazard_result(screen_candidate_parcels(load_geohazard_input(source)), output)
            self.assertFalse(output.exists())

    def test_adapt_source_is_scanned_before_strict_parsing(self):
        data = json.loads(ADAPT_PATH.read_text(encoding="utf-8"))
        data["site"]["adaptationAssumptions"][0]["basis"] = "987 Example Road"
        with self.assertRaises(ConfigError):
            parse_geohazard_input(data)

    def test_adaptation_basis_rejects_apn_and_parcel_identifiers(self):
        data = json.loads(ADAPT_PATH.read_text(encoding="utf-8"))
        data["site"]["adaptationAssumptions"][0]["basis"] = (
            "Synthetic assumption tied to APN 123-456-789 and parcel ID 98765"
        )
        with self.assertRaises(ConfigError):
            parse_geohazard_input(data)

    def test_textual_property_identifier_patterns_fail_closed(self):
        values = (
            "APN 123-456-789",
            "assessor parcel number 12345",
            "parcel ID 98765",
            "tax ID: 4567",
            "deed book 12 page 34",
            "lot 12 block 3",
            "Lot ID: A-12",
            "Block #7",
        )
        for value in values:
            with self.subTest(value=value):
                with self.assertRaises(ConfigError):
                    reject_private_location_data(value)
        reject_private_location_data("Generic parcel screening prose and block foundations remain synthetic.")

    def test_document_loader_validates_and_preserves_envelope(self):
        document = load_geohazard_document(SCREEN_PATH)
        self.assertEqual(document["mode"], "screen")
        self.assertEqual(document["analysisId"], "AN-SITE-SCREEN-001")
        self.assertIn("provenance", document)


class GeometryTests(unittest.TestCase):
    def test_line_distance_projection_endpoint_and_intersection(self):
        line = LocalFeature("FEATURE-LINE", "WATERWAY", (LocalPoint(3, -2), LocalPoint(3, 2)), 1)
        self.assertEqual(minimum_feature_distance(line), 3)
        endpoint = LocalFeature("FEATURE-LINE", "WATERWAY", (LocalPoint(3, 4), LocalPoint(8, 4)), 0)
        self.assertEqual(minimum_feature_distance(endpoint), 5)
        crossing = LocalFeature("FEATURE-LINE", "WATERWAY", (LocalPoint(-2, -2), LocalPoint(2, 2)), 0)
        self.assertEqual(minimum_feature_distance(crossing), 0)

    def test_polygon_distance_inside_and_boundary(self):
        far = LocalFeature(
            "FEATURE-AREA", "WETLAND",
            (LocalPoint(3, 3), LocalPoint(5, 3), LocalPoint(5, 5), LocalPoint(3, 5)), 0,
        )
        self.assertAlmostEqual(minimum_feature_distance(far), math.sqrt(18))
        inside = LocalFeature(
            "FEATURE-AREA", "WETLAND",
            (LocalPoint(-2, -2), LocalPoint(2, -2), LocalPoint(2, 2), LocalPoint(-2, 2)), 0,
        )
        self.assertEqual(minimum_feature_distance(inside), 0)
        boundary = LocalFeature(
            "FEATURE-AREA", "WETLAND",
            (LocalPoint(0, -2), LocalPoint(2, -2), LocalPoint(2, 2), LocalPoint(0, 2)), 0,
        )
        self.assertEqual(minimum_feature_distance(boundary), 0)

    def test_invalid_feature_geometry_is_rejected(self):
        bow_tie = LocalFeature(
            "FEATURE-AREA", "WETLAND",
            (LocalPoint(-1, -1), LocalPoint(1, 1), LocalPoint(-1, 1), LocalPoint(1, -1)), 0,
        )
        with self.assertRaises(ConfigError):
            minimum_feature_distance(bow_tie)
        with self.assertRaises(ConfigError):
            minimum_feature_distance(LocalFeature(
                "FEATURE-LINE", "WATERWAY", (LocalPoint(0, 0), LocalPoint(0, 0)), 0,
            ))


class RiskPermitAccessTests(unittest.TestCase):
    def setUp(self):
        self.parcels = load_geohazard_input(SCREEN_PATH)
        self.clean = self.parcels[0]

    def factors(self, **changes):
        return replace(self.clean.factors, **changes)

    def test_equal_setback_is_modeled_low_but_ahj_reviewed(self):
        water = replace(
            self.clean.factors.water, nearest_waterway_distance_m=40, nearest_wetland_distance_m=50,
        )
        risks = risk_by_name(self.factors(water=water))
        self.assertEqual(risks["WATERWAY_SETBACK"].level, RiskLevel.LOW)
        self.assertIn("SG-006", risks["WATERWAY_SETBACK"].required_gate_ids)
        self.assertEqual(risks["WETLAND_SETBACK"].level, RiskLevel.LOW)

    def test_inside_setback_and_null_distance_are_not_averaged(self):
        water = replace(self.clean.factors.water, nearest_waterway_distance_m=39, nearest_wetland_distance_m=None)
        risks = risk_by_name(self.factors(water=water))
        self.assertEqual(risks["WATERWAY_SETBACK"].level, RiskLevel.HIGH)
        self.assertEqual(risks["WETLAND_SETBACK"].level, RiskLevel.UNKNOWN)
        self.assertTrue(risks["WETLAND_SETBACK"].required_gate_ids)

    def test_karst_groundwater_flood_and_slope_domains_remain_independent(self):
        factors = self.parcels[1].factors
        risks = risk_by_name(factors)
        for domain in ("CLOSED_DEPRESSION", "KARST_BEDROCK", "GROUNDWATER", "FLOOD_100YR", "SLOPE_STABILITY"):
            self.assertEqual(risks[domain].level, RiskLevel.HIGH, domain)
        self.assertEqual(len(risks), 16)
        self.assertEqual(risks["ROAD_AXLE"].level, RiskLevel.LOW)

    def test_null_groundwater_karst_flood_and_slope_are_unknown(self):
        karst = replace(self.clean.factors.karst, karst_bedrock_depth_m=None)
        water = replace(self.clean.factors.water, groundwater_depth_m=None, flood_100yr_depth_m=None)
        slope = replace(self.clean.factors.slope, modeled_factor_of_safety=None)
        risks = risk_by_name(self.factors(karst=karst, water=water, slope=slope))
        for domain in ("KARST_BEDROCK", "GROUNDWATER", "FLOOD_100YR", "SLOPE_STABILITY"):
            self.assertEqual(risks[domain].level, RiskLevel.UNKNOWN)
            self.assertTrue(risks[domain].required_gate_ids)

    def test_expansive_clay_land_shift_and_climate_flags(self):
        slope = replace(self.clean.factors.slope, expansive_clay_risk=RiskLevel.UNKNOWN, land_shift_rate_mm_year=9)
        climate = replace(
            self.clean.factors.climate, mean_daily_insolation_kwh_m2_day=2,
            winter_design_temperature_c=-25,
        )
        risks = risk_by_name(self.factors(slope=slope, climate=climate))
        self.assertEqual(risks["EXPANSIVE_CLAY"].level, RiskLevel.UNKNOWN)
        self.assertEqual(risks["LAND_SHIFT"].level, RiskLevel.HIGH)
        self.assertEqual(risks["SOLAR_RESOURCE"].level, RiskLevel.MODERATE)
        self.assertEqual(risks["WINTER_DESIGN"].level, RiskLevel.MODERATE)

    def test_access_overload_unknown_limits_and_clearance_math(self):
        road = replace(
            self.clean.factors.road, lowest_route_axle_limit_kg=None, minimum_overhead_clearance_m=4,
        )
        risks = risk_by_name(self.factors(road=road))
        self.assertEqual(risks["ROAD_AXLE"].level, RiskLevel.UNKNOWN)
        self.assertEqual(risks["OVERHEAD_CLEARANCE"].level, RiskLevel.HIGH)
        self.assertEqual(risks["OVERHEAD_CLEARANCE"].threshold, 4.5)

    def test_acoustic_free_field_comparison_and_lower_bound(self):
        privacy = replace(
            self.clean.factors.privacy, source_dba_at_15m=65, receiver_target_dba=45, ambient_dba=50,
            nearest_sightline_distance_m=20,
        )
        risks = risk_by_name(self.factors(privacy=privacy))
        expected = max(15, 15 * 10 ** ((65 - 50) / 20))
        self.assertAlmostEqual(risks["ACOUSTIC_PRIVACY"].threshold, expected)
        self.assertEqual(risks["ACOUSTIC_PRIVACY"].level, RiskLevel.MODERATE)
        quiet = replace(privacy, source_dba_at_15m=10, nearest_sightline_distance_m=10)
        quiet_risks = risk_by_name(self.factors(privacy=quiet))
        self.assertEqual(quiet_risks["ACOUSTIC_PRIVACY"].threshold, 15)
        self.assertEqual(quiet_risks["ACOUSTIC_PRIVACY"].level, RiskLevel.MODERATE)

    def test_permit_candidate_is_never_an_exemption_determination(self):
        assessments = assess_permits(self.clean.factors.permits)
        topics = {item.topic: item for item in assessments}
        self.assertEqual(
            topics["RURAL_AGRICULTURAL_ACCESSORY_EXEMPTION"].finding, PermitFinding.EXEMPTION_CANDIDATE,
        )
        self.assertEqual(topics["AHJ_DETERMINATION"].finding, PermitFinding.AHJ_CONFIRMATION_REQUIRED)
        self.assertTrue(all(item.ahj_gate_id == "SG-006" for item in assessments))

    def test_permit_equality_well_septic_and_culvert_trigger(self):
        assessments = assess_permits(self.parcels[1].factors.permits)
        topics = {item.topic: item for item in assessments}
        self.assertEqual(self.parcels[1].factors.permits.ground_disturbance_m2, 1000)
        self.assertEqual(self.parcels[1].factors.permits.swppp_trigger_area_m2, 1000)
        for topic in ("GRADING_SWPPP", "WELL_SEPTIC", "DRIVEWAY_CULVERT"):
            self.assertEqual(topics[topic].finding, PermitFinding.TRIGGERED)

    def test_permit_parser_rejects_resolved_ahj(self):
        data = json.loads(SCREEN_PATH.read_text(encoding="utf-8"))
        data["candidates"][0]["factors"]["permits"]["ahjDeterminationObtained"] = True
        with self.assertRaises(ConfigError):
            parse_geohazard_input(data)


class ScreeningTests(unittest.TestCase):
    def setUp(self):
        self.parcels = load_geohazard_input(SCREEN_PATH)
        self.result = screen_candidate_parcels(self.parcels)

    def test_candidate_review_reject_decisions_and_deterministic_sort(self):
        self.assertEqual(
            [item.anonymous_label for item in self.result.parcels],
            ["CANDIDATE-C", "CANDIDATE-B", "CANDIDATE-A"],
        )
        self.assertEqual(
            [item.decision for item in self.result.parcels],
            [ScreeningDecision.REJECT_ON_MODELED_CONSTRAINT,
             ScreeningDecision.ENGINEERING_REVIEW, ScreeningDecision.RELATIVE_CANDIDATE],
        )

    def test_access_review_spoil_caps_and_all_unresolved_gates(self):
        by_label = {item.anonymous_label: item for item in self.result.parcels}
        self.assertFalse(by_label["CANDIDATE-A"].road_access_review_required)
        self.assertTrue(by_label["CANDIDATE-B"].road_access_review_required)
        self.assertTrue(by_label["CANDIDATE-C"].road_access_review_required)
        self.assertEqual(by_label["CANDIDATE-A"].privacy_berm_volume_m3, 120)
        self.assertEqual(by_label["CANDIDATE-B"].privacy_berm_volume_m3, 60)
        gate_ids = tuple(gate.gate_id for gate in self.result.human_gates)
        self.assertEqual(gate_ids, tuple(f"SG-{index:03d}" for index in range(1, 10)))
        for parcel in self.result.parcels:
            self.assertEqual(parcel.unresolved_gate_ids, gate_ids)
        self.assertTrue(all(gate.status == "UNRESOLVED" for gate in self.result.human_gates))

    def test_output_has_no_raw_features_purchase_or_location_claims(self):
        text = geohazard_result_json(self.result)
        self.assertNotIn("featureLabel", text)
        self.assertNotIn("vertices_local_m", text)
        self.assertNotIn("FEATURE-WATER", text)
        self.assertFalse(self.result.purchase_recommendation_made)
        self.assertFalse(self.result.location_data_retained)
        self.assertFalse(self.result.physical_validation_performed)

    def test_repeat_calls_and_facade_are_byte_identical(self):
        first = geohazard_result_json(self.result)
        second = geohazard_result_json(SiteAdvisor().screen(self.parcels))
        self.assertEqual(first, second)

    def test_duplicate_candidate_labels_fail(self):
        with self.assertRaises(ConfigError):
            screen_candidate_parcels((self.parcels[0], self.parcels[0]))
        data = json.loads(SCREEN_PATH.read_text(encoding="utf-8"))
        data["candidates"][1]["anonymousLabel"] = data["candidates"][0]["anonymousLabel"]
        with self.assertRaises(ConfigError):
            parse_geohazard_input(data)

    def test_writer_and_frozen_results(self):
        with tempfile.TemporaryDirectory() as temp:
            path = write_geohazard_result(self.result, temp)
            self.assertEqual(path.read_text(encoding="utf-8"), geohazard_result_json(self.result))
        with self.assertRaises(FrozenInstanceError):
            self.result.mode = "adapt"


class AdaptationTests(unittest.TestCase):
    def setUp(self):
        self.site = load_geohazard_input(ADAPT_PATH)
        self.result = adapt_to_existing_site(self.site)

    def quiet_site(self):
        factors = self.site.factors
        quiet = replace(
            factors,
            karst=replace(factors.karst, karst_bedrock_depth_m=40, subsidence_risk=RiskLevel.LOW),
            water=replace(
                factors.water, groundwater_depth_m=8, flood_100yr_depth_m=0,
                buoyancy_displaced_volume_m3=0,
            ),
            slope=replace(
                factors.slope, expansive_clay_risk=RiskLevel.LOW, land_shift_rate_mm_year=1,
                modeled_factor_of_safety=1.6,
            ),
            privacy=replace(
                factors.privacy, required_visual_screen_height_m=0, privacy_berm_length_m=0,
                privacy_berm_cross_section_m2=0,
            ),
        )
        return replace(self.site, factors=quiet)

    def adaptation(self, result, kind):
        return next(item for item in result.adaptations if item.kind is kind)

    def test_canonical_trigger_order_ids_mound_and_raft(self):
        self.assertEqual(
            [item.kind for item in self.result.adaptations],
            [AdaptationKind.SHALLOW_MOUND, AdaptationKind.CELLULAR_RAFT,
             AdaptationKind.ANTI_FLOTATION_COLLAR, AdaptationKind.REDUNDANT_SOLAR_DRAINAGE,
             AdaptationKind.PRIVACY_SPOIL_BERM],
        )
        self.assertEqual([item.adaptation_id for item in self.result.adaptations],
                         ["SA-001", "SA-002", "SA-003", "SA-004", "SA-005"])
        mound = self.adaptation(self.result, AdaptationKind.SHALLOW_MOUND)
        raft = self.adaptation(self.result, AdaptationKind.CELLULAR_RAFT)
        self.assertEqual(mound.construction_strategy, ConstructionStrategy.SEMI_BURIED_EARTH_BERMED_MOUND)
        self.assertEqual(raft.foundation_strategy, FoundationStrategy.STIFFENED_CELLULAR_RAFT_ON_GEOGRID)
        self.assertNotIn(ConstructionStrategy.DEEP_CUT_AND_COVER,
                         [item.construction_strategy for item in self.result.adaptations])
        self.assertEqual(self.result.anonymous_label, "EXISTING-SITE")

    def test_multiple_shallow_causes_create_only_one_mound(self):
        mound = self.adaptation(self.result, AdaptationKind.SHALLOW_MOUND)
        self.assertIn("groundwater", mound.trigger_reason)
        self.assertIn("karst", mound.trigger_reason)
        self.assertEqual(sum(item.kind is AdaptationKind.SHALLOW_MOUND for item in self.result.adaptations), 1)

    def test_shallow_karst_independently_triggers_mound(self):
        site = self.quiet_site()
        site = replace(site, factors=replace(site.factors, karst=replace(site.factors.karst, karst_bedrock_depth_m=2)))
        result = adapt_to_existing_site(site)
        self.assertIn(AdaptationKind.SHALLOW_MOUND, [item.kind for item in result.adaptations])

    def test_unknown_expansive_soil_and_land_shift_trigger_raft(self):
        quiet = self.quiet_site()
        unknown = replace(quiet, factors=replace(
            quiet.factors, slope=replace(quiet.factors.slope, expansive_clay_risk=RiskLevel.UNKNOWN),
        ))
        self.assertIn(AdaptationKind.CELLULAR_RAFT,
                      [item.kind for item in adapt_to_existing_site(unknown).adaptations])
        shifting = replace(quiet, factors=replace(
            quiet.factors, slope=replace(quiet.factors.slope, land_shift_rate_mm_year=6),
        ))
        self.assertIn(AdaptationKind.CELLULAR_RAFT,
                      [item.kind for item in adapt_to_existing_site(shifting).adaptations])

    def test_anti_flotation_volume_matches_independent_arithmetic(self):
        water = self.site.factors.water
        required = self.site.anti_flotation_required_factor
        uplift = water.water_density_kg_m3 * 9.80665 * water.buoyancy_displaced_volume_m3
        resisting = water.resisting_mass_kg * 9.80665
        expected = max(0, (required * uplift - resisting) / (
            9.80665 * (water.concrete_density_kg_m3 - required * water.collar_submerged_fraction
                       * water.water_density_kg_m3)
        ))
        collar = self.adaptation(self.result, AdaptationKind.ANTI_FLOTATION_COLLAR)
        self.assertAlmostEqual(collar.anti_flotation_deadweight_volume_m3, expected)
        self.assertAlmostEqual(expected, 6.06060606060606)

    def test_nonpositive_density_denominator_fails_explicitly(self):
        factors = self.site.factors
        bad = replace(factors, water=replace(factors.water, concrete_density_kg_m3=500))
        with self.assertRaisesRegex(ConfigError, "denominator"):
            adapt_to_existing_site(replace(self.site, factors=bad))

    def test_zero_volume_and_sufficient_resistance_do_not_create_collar(self):
        quiet = self.quiet_site()
        zero = adapt_to_existing_site(quiet)
        self.assertFalse(zero.adaptations)
        water = replace(quiet.factors.water, buoyancy_displaced_volume_m3=8, resisting_mass_kg=100000)
        sufficient = adapt_to_existing_site(replace(quiet, factors=replace(quiet.factors, water=water)))
        self.assertNotIn(AdaptationKind.ANTI_FLOTATION_COLLAR,
                         [item.kind for item in sufficient.adaptations])

    def test_redundant_solar_drainage_two_concepts_and_electrical_gate(self):
        drainage = self.adaptation(self.result, AdaptationKind.REDUNDANT_SOLAR_DRAINAGE)
        self.assertEqual(drainage.redundant_solar_sump_count, 2)
        self.assertIn("SG-008", drainage.required_gate_ids)
        self.assertIn("not a drainage design", drainage.trigger_reason)

    def test_spoil_berm_caps_at_available_and_reports_shortfall(self):
        berm = self.adaptation(self.result, AdaptationKind.PRIVACY_SPOIL_BERM)
        self.assertEqual(berm.privacy_berm_volume_m3, 80)
        self.assertLessEqual(berm.privacy_berm_volume_m3, self.site.factors.privacy.available_compacted_spoil_m3)
        self.assertIn("40.000000", berm.trigger_reason)
        self.assertNotIn("authorized", berm.trigger_reason.lower())

    def test_signed_cost_schedule_and_labor_deltas_preserve_order(self):
        self.assertEqual(self.result.total_cost_delta, 33100)
        self.assertEqual(self.result.total_schedule_delta_h, 136)
        self.assertEqual(sum(item.delta.labor_delta_h for item in self.result.adaptations), 374)
        self.assertEqual([item.delta.adaptation_id for item in self.result.adaptations],
                         ["SA-001", "SA-002", "SA-003", "SA-004", "SA-005"])
        self.assertEqual(self.result.adaptations[0].delta.cost_delta, -12000)
        self.assertEqual(self.result.adaptations[0].delta.schedule_delta_h, -80)

    def test_waterway_and_access_reviews_trigger_with_assumptions(self):
        quiet = self.quiet_site()
        factors = replace(
            quiet.factors,
            water=replace(quiet.factors.water, nearest_waterway_distance_m=None),
            road=replace(quiet.factors.road, minimum_overhead_clearance_m=None),
        )
        extras = (
            replace(self.site.adaptation_assumptions[0], kind=AdaptationKind.WATERWAY_SETBACK),
            replace(self.site.adaptation_assumptions[0], kind=AdaptationKind.ACCESS_REVIEW),
        )
        result = adapt_to_existing_site(replace(quiet, factors=factors, adaptation_assumptions=extras))
        kinds = [item.kind for item in result.adaptations]
        self.assertIn(AdaptationKind.WATERWAY_SETBACK, kinds)
        self.assertIn(AdaptationKind.ACCESS_REVIEW, kinds)

    def test_missing_triggered_assumption_fails_without_output(self):
        site = replace(
            self.site,
            adaptation_assumptions=tuple(
                item for item in self.site.adaptation_assumptions if item.kind is not AdaptationKind.SHALLOW_MOUND
            ),
        )
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "output"
            with self.assertRaisesRegex(ConfigError, "no explicit AdaptationAssumption"):
                write_geohazard_result(adapt_to_existing_site(site), output)
            self.assertFalse(output.exists())

    def test_duplicate_assumption_and_currency_mismatch_fail(self):
        duplicate = self.site.adaptation_assumptions + self.site.adaptation_assumptions[:1]
        with self.assertRaises(ConfigError):
            adapt_to_existing_site(replace(self.site, adaptation_assumptions=duplicate))
        with self.assertRaisesRegex(ConfigError, "currency"):
            geohazard_result_json(replace(self.result, currency="EUR"))

    def test_human_gates_and_no_authorization_survive(self):
        ids = tuple(f"SG-{index:03d}" for index in range(1, 10))
        self.assertEqual(self.result.human_gate_ids, ids)
        self.assertEqual(tuple(item.gate_id for item in self.result.human_gates), ids)
        self.assertTrue(all(item.status == "UNRESOLVED" for item in self.result.human_gates))
        self.assertFalse(self.result.construction_authorized)
        self.assertFalse(self.result.site_engineering_complete)
        self.assertFalse(self.result.location_data_retained)
        self.assertFalse(self.result.physical_validation_performed)

    def test_repeat_calls_and_writer_are_deterministic(self):
        first = geohazard_result_json(self.result)
        second = geohazard_result_json(SiteAdvisor().adapt(self.site))
        self.assertEqual(first, second)
        with tempfile.TemporaryDirectory() as temp:
            path = write_geohazard_result(self.result, temp)
            self.assertEqual(path.read_bytes(), first.encode("utf-8"))

    def test_nonfinite_result_is_rejected_before_output(self):
        bad = replace(self.result.adaptations[0].delta, cost_delta=math.nan)
        adaptation = replace(self.result.adaptations[0], delta=bad)
        result = replace(
            self.result, adaptations=(adaptation,) + self.result.adaptations[1:], total_cost_delta=math.nan,
        )
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "output"
            with self.assertRaises(ConfigError):
                write_geohazard_result(result, output)
            self.assertFalse(output.exists())


@unittest.skipUnless(importlib.util.find_spec("jsonschema"), "optional jsonschema is unavailable")
class SchemaTests(unittest.TestCase):
    def test_schema_and_both_examples_validate_as_draft_2020_12(self):
        from jsonschema import Draft202012Validator

        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        for path in (SCREEN_PATH, ADAPT_PATH):
            with self.subTest(path=path.name):
                validator.validate(json.loads(path.read_text(encoding="utf-8")))

    def test_schema_rejects_empty_required_string(self):
        from jsonschema import Draft202012Validator, ValidationError

        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["analysisId"]["pattern"], "\\S")
        data = json.loads(SCREEN_PATH.read_text(encoding="utf-8"))
        data["analysisId"] = "   "
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema).validate(data)


if __name__ == "__main__":
    unittest.main()
