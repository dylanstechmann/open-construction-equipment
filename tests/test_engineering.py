# SPDX-License-Identifier: Apache-2.0
import copy
from dataclasses import FrozenInstanceError
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from open_construction_equipment.config import ConfigError
from open_construction_equipment.engineering import (
    ANALYSIS_ID,
    EXPECTED_TRACE_IDS,
    analysis_result_json,
    calculate_static_longitudinal,
    load_analysis_input,
    normalized_analysis_input,
    parse_analysis_input,
    write_analysis_result,
)
from open_construction_equipment.validation import repository_root

ROOT = repository_root()
INPUT_PATH = ROOT / "examples/analysis/synthetic-lc001.json"
SCHEMA_PATH = ROOT / "schemas/engineering-analysis.schema.json"


class EngineeringTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def write(self, data):
        path = Path(self.temp.name) / "analysis.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def calculate(self, data=None):
        return calculate_static_longitudinal(parse_analysis_input(copy.deepcopy(data or self.data)))

    def test_independently_hand_calculated_sample(self):
        result = self.calculate()
        values = result["results"]
        gravity = 9.80665
        self.assertEqual(ANALYSIS_ID, "AN-LC-001A")
        self.assertEqual(values["totalMass_kg"], 2020)
        self.assertAlmostEqual(values["combinedCgX_m"], 291 / 2020, places=14)
        self.assertEqual(values["resultantX_m"], values["combinedCgX_m"])
        self.assertAlmostEqual(values["signedLoadMoments_Nm"]["aboutFrontSupport"], -1325 * gravity)
        self.assertAlmostEqual(values["signedLoadMoments_Nm"]["aboutRearSupport"], 2109 * gravity)
        self.assertAlmostEqual(values["staticMomentMargins_Nm"]["front"], 1325 * gravity)
        self.assertAlmostEqual(values["staticMomentMargins_Nm"]["rear"], 2109 * gravity)
        self.assertAlmostEqual(values["staticMomentMargins_Nm"]["minimum"], 1325 * gravity)
        self.assertAlmostEqual(values["supportReactions_N"]["front"], 2109 * gravity / 1.7)
        self.assertAlmostEqual(values["supportReactions_N"]["rear"], 1325 * gravity / 1.7)
        self.assertAlmostEqual(
            sum(values["supportReactions_N"].values()), 2020 * gravity
        )
        self.assertTrue(values["resultantWithinSupportInterval"])

    def test_resultant_exactly_on_front_support_boundary(self):
        self.data["inputs"]["machine"]["cgX_m"]["value"] = 0.8
        self.data["inputs"]["attachment"]["mass_kg"]["value"] = 0
        self.data["inputs"]["payload"]["mass_kg"]["value"] = 0
        values = self.calculate()["results"]
        self.assertEqual(values["resultantX_m"], 0.8)
        self.assertEqual(values["staticMomentMargins_Nm"]["front"], 0)
        self.assertEqual(values["staticMomentMargins_Nm"]["minimum"], 0)
        self.assertTrue(values["resultantWithinSupportInterval"])
        self.assertAlmostEqual(values["supportReactions_N"]["rear"], 0)

    def test_resultant_exactly_on_rear_support_boundary(self):
        self.data["inputs"]["machine"]["cgX_m"]["value"] = -0.9
        self.data["inputs"]["attachment"]["mass_kg"]["value"] = 0
        self.data["inputs"]["payload"]["mass_kg"]["value"] = 0
        values = self.calculate()["results"]
        self.assertEqual(values["resultantX_m"], -0.9)
        self.assertEqual(values["staticMomentMargins_Nm"]["rear"], 0)
        self.assertEqual(values["staticMomentMargins_Nm"]["minimum"], 0)
        self.assertTrue(values["resultantWithinSupportInterval"])
        self.assertAlmostEqual(values["supportReactions_N"]["front"], 0)

    def test_resultant_outside_support_interval(self):
        self.data["inputs"]["machine"]["cgX_m"]["value"] = 1.0
        self.data["inputs"]["attachment"]["mass_kg"]["value"] = 0
        self.data["inputs"]["payload"]["mass_kg"]["value"] = 0
        values = self.calculate()["results"]
        self.assertFalse(values["resultantWithinSupportInterval"])
        self.assertLess(values["staticMomentMargins_Nm"]["minimum"], 0)
        self.assertLess(values["supportReactions_N"]["rear"], 0)

    def test_zero_payload_has_no_special_zero_or_infinite_boundary(self):
        self.data["inputs"]["payload"]["mass_kg"]["value"] = 0
        values = self.calculate()["results"]
        self.assertEqual(values["totalMass_kg"], 1840)
        self.assertAlmostEqual(values["combinedCgX_m"], 12 / 1840)
        boundary = values["forwardZeroStaticMarginPayloadBoundary"]
        self.assertAlmostEqual(boundary["payloadMass_kg"], 1460 / 0.75)
        self.assertIsNone(boundary["reason"])

    def test_forward_zero_margin_boundary_matches_analytic_solution(self):
        values = self.calculate()["results"]
        boundary = values["forwardZeroStaticMarginPayloadBoundary"]
        self.assertAlmostEqual(boundary["payloadMass_kg"], 1946.6666666666667)
        self.assertIsNone(boundary["reason"])
        analytic_mass = -(1600 * (-0.15 - 0.8) + 240 * (1.05 - 0.8)) / (1.55 - 0.8)
        self.assertAlmostEqual(boundary["payloadMass_kg"], analytic_mass)
        self.data["inputs"]["payload"]["mass_kg"]["value"] = analytic_mass
        at_boundary = self.calculate()["results"]
        self.assertAlmostEqual(at_boundary["resultantX_m"], 0.8)
        self.assertAlmostEqual(at_boundary["staticMomentMargins_Nm"]["front"], 0, places=8)

    def test_undefined_forward_boundary_at_or_behind_front_support(self):
        for coordinate in (0.8, 0.0, -10.0):
            with self.subTest(coordinate=coordinate):
                self.data["inputs"]["payload"]["cgX_m"]["value"] = coordinate
                boundary = self.calculate()["results"]["forwardZeroStaticMarginPayloadBoundary"]
                self.assertIsNone(boundary["payloadMass_kg"])
                self.assertIn("not forward", boundary["reason"])

    def test_zero_or_negative_baseline_has_no_positive_boundary(self):
        for coordinate in (0.8, 1.0):
            with self.subTest(coordinate=coordinate):
                self.data["inputs"]["machine"]["cgX_m"]["value"] = coordinate
                self.data["inputs"]["attachment"]["mass_kg"]["value"] = 0
                self.data["inputs"]["payload"]["mass_kg"]["value"] = 0
                boundary = self.calculate()["results"]["forwardZeroStaticMarginPayloadBoundary"]
                self.assertIsNone(boundary["payloadMass_kg"])
                self.assertIn("zero or negative", boundary["reason"])

    def test_negative_algebraic_candidate_is_not_reported_as_boundary(self):
        self.data["inputs"]["machine"]["cgX_m"]["value"] = 1.0
        self.data["inputs"]["attachment"]["mass_kg"]["value"] = 0
        self.data["inputs"]["payload"]["mass_kg"]["value"] = 0
        self.data["inputs"]["payload"]["cgX_m"]["value"] = 0.0
        boundary = self.calculate()["results"]["forwardZeroStaticMarginPayloadBoundary"]
        self.assertIsNone(boundary["payloadMass_kg"])
        self.assertIsNotNone(boundary["reason"])

    def test_invalid_support_ordering_is_rejected(self):
        for rear, front in ((0.8, 0.8), (1.0, 0.8)):
            with self.subTest(rear=rear, front=front):
                self.data["inputs"]["supports"]["rearX_m"]["value"] = rear
                self.data["inputs"]["supports"]["frontX_m"]["value"] = front
                with self.assertRaisesRegex(ConfigError, "greater than"):
                    parse_analysis_input(self.data)

    def test_nonfinite_boolean_and_negative_values_are_rejected(self):
        for value in (float("nan"), float("inf"), float("-inf"), True, -1):
            for point in ("machine", "attachment", "payload"):
                with self.subTest(value=value, point=point):
                    data = copy.deepcopy(self.data)
                    data["inputs"][point]["mass_kg"]["value"] = value
                    with self.assertRaises(ConfigError):
                        parse_analysis_input(data)

    def test_zero_bare_machine_mass_is_rejected(self):
        self.data["inputs"]["machine"]["mass_kg"]["value"] = 0
        with self.assertRaises(ConfigError):
            parse_analysis_input(self.data)

    def test_every_numeric_input_requires_provenance(self):
        quantities = [
            self.data["inputs"][point][key]
            for point in ("machine", "attachment", "payload")
            for key in ("mass_kg", "cgX_m")
        ] + [self.data["inputs"]["supports"][key] for key in ("rearX_m", "frontX_m")]
        self.assertEqual(len(quantities), 8)
        for index in range(len(quantities)):
            with self.subTest(index=index):
                data = copy.deepcopy(self.data)
                data_quantities = [
                    data["inputs"][point][key]
                    for point in ("machine", "attachment", "payload")
                    for key in ("mass_kg", "cgX_m")
                ] + [data["inputs"]["supports"][key] for key in ("rearX_m", "frontX_m")]
                del data_quantities[index]["provenance"]
                with self.assertRaisesRegex(ConfigError, "missing fields: provenance"):
                    parse_analysis_input(data)

    def test_missing_provenance_trace_or_false_origin_is_rejected(self):
        provenance = self.data["inputs"]["machine"]["mass_kg"]["provenance"]
        provenance["traceIds"] = []
        with self.assertRaisesRegex(ConfigError, "non-empty"):
            parse_analysis_input(self.data)
        provenance["traceIds"] = ["LC-001"]
        provenance["cadDerived"] = True
        with self.assertRaisesRegex(ConfigError, "explicitly deny"):
            parse_analysis_input(self.data)

    def test_unknown_or_invalid_trace_ids_are_rejected(self):
        self.data["traceIds"][-1] = "IF-MEC-999"
        with self.assertRaisesRegex(ConfigError, "canonical order"):
            parse_analysis_input(self.data)
        self.data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
        self.data["inputs"]["payload"]["mass_kg"]["provenance"]["traceIds"] = ["HZ-999"]
        with self.assertRaisesRegex(ConfigError, "recognized analysis trace"):
            parse_analysis_input(self.data)

    def test_stable_analysis_id_and_status_cannot_be_changed(self):
        self.data["analysisId"] = "AN-OTHER"
        with self.assertRaisesRegex(ConfigError, "AN-LC-001A"):
            parse_analysis_input(self.data)
        self.data["analysisId"] = ANALYSIS_ID
        self.data["acceptanceStatus"] = "ASSESSED"
        with self.assertRaisesRegex(ConfigError, "NOT_ASSESSED"):
            parse_analysis_input(self.data)

    def test_out_of_float_range_integer_is_a_controlled_analysis_input_error(self):
        self.data["inputs"]["machine"]["mass_kg"]["value"] = 10**400
        with self.assertRaisesRegex(ConfigError, "finite number"):
            load_analysis_input(self.write(self.data))

    def test_whitespace_only_strings_are_rejected_by_runtime_and_schema(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["syntheticNotice"]["pattern"], r"\S")
        self.assertEqual(schema["$defs"]["provenance"]["properties"]["statement"]["pattern"], r"\S")
        validator = None
        if importlib.util.find_spec("jsonschema") is not None:
            import jsonschema
            jsonschema.Draft202012Validator.check_schema(schema)
            validator = jsonschema.Draft202012Validator(schema)
        for path in ("syntheticNotice", "provenance.statement"):
            with self.subTest(path=path):
                data = copy.deepcopy(self.data)
                if path == "syntheticNotice":
                    data["syntheticNotice"] = " \t\n "
                else:
                    data["inputs"]["machine"]["mass_kg"]["provenance"]["statement"] = " \t\n "
                with self.assertRaisesRegex(ConfigError, "non-empty string"):
                    parse_analysis_input(data)
                if validator is not None:
                    self.assertFalse(validator.is_valid(data))

    def test_duplicate_json_keys_are_rejected(self):
        path = Path(self.temp.name) / "duplicate.json"
        path.write_text('{"analysisId": "AN-LC-001A", "analysisId": "other"}', encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "duplicate JSON key"):
            load_analysis_input(path)

    def test_nonstandard_json_constants_are_rejected(self):
        path = Path(self.temp.name) / "nan.json"
        path.write_text('{"value": NaN}', encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "non-standard JSON"):
            load_analysis_input(path)

    def test_units_are_explicit_without_silent_conversion(self):
        self.data["inputs"]["machine"]["mass_kg"]["unit"] = "g"
        with self.assertRaisesRegex(ConfigError, "no units conversion"):
            parse_analysis_input(self.data)

    def test_unknown_and_missing_fields_are_rejected(self):
        self.data["inputs"]["supports"]["extra"] = 1
        with self.assertRaisesRegex(ConfigError, "unknown fields"):
            parse_analysis_input(self.data)
        del self.data["inputs"]["supports"]["extra"]
        del self.data["inputs"]["payload"]["cgX_m"]
        with self.assertRaisesRegex(ConfigError, "missing fields"):
            parse_analysis_input(self.data)

    def test_schema_and_runtime_agree_on_canonical_example(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["properties"]["analysisId"]["const"], ANALYSIS_ID)
        self.assertEqual(
            [item["const"] for item in schema["properties"]["traceIds"]["prefixItems"]],
            list(EXPECTED_TRACE_IDS),
        )
        self.assertEqual(schema["properties"]["acceptanceStatus"]["const"], "NOT_ASSESSED")
        self.assertEqual(schema["properties"]["reviewStatus"]["const"], "UNREVIEWED")
        self.assertIs(schema["properties"]["physicalValidationPerformed"]["const"], False)
        if importlib.util.find_spec("jsonschema") is not None:
            import jsonschema
            jsonschema.Draft202012Validator.check_schema(schema)
            jsonschema.Draft202012Validator(schema).validate(self.data)

    def test_deterministic_hash_serialization_and_file_output(self):
        model = load_analysis_input(INPUT_PATH)
        first = calculate_static_longitudinal(model)
        second = calculate_static_longitudinal(load_analysis_input(INPUT_PATH))
        canonical = json.dumps(
            normalized_analysis_input(model), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        self.assertEqual(first["inputSha256"], hashlib.sha256(canonical.encode("utf-8")).hexdigest())
        self.assertEqual(analysis_result_json(first), analysis_result_json(second))
        output = write_analysis_result(first, Path(self.temp.name) / "nested")
        self.assertEqual(output.read_bytes(), analysis_result_json(second).encode("utf-8"))
        self.assertTrue(output.read_bytes().endswith(b"\n"))

    def test_input_models_are_immutable_and_output_is_not_an_acceptance_verdict(self):
        model = load_analysis_input(INPUT_PATH)
        with self.assertRaises(FrozenInstanceError):
            model.analysis_id = "changed"
        result = calculate_static_longitudinal(model)
        self.assertEqual(result["acceptanceStatus"], "NOT_ASSESSED")
        self.assertEqual(result["reviewStatus"], "UNREVIEWED")
        self.assertIs(result["physicalValidationPerformed"], False)
        for excluded in ("slope", "braking", "turning", "terrain", "track slip", "fatigue", "hydraulic", "standards"):
            self.assertIn(excluded, " ".join(result["exclusions"]))


if __name__ == "__main__":
    unittest.main()
