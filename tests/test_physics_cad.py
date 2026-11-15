# SPDX-License-Identifier: Apache-2.0
import ast
import copy
from dataclasses import FrozenInstanceError, replace
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

from open_construction_equipment.config import ConfigError
from open_construction_equipment.physics import (
    BearingInput,
    BuoyancyInput,
    ConcreteCuringInput,
    EvidenceStatus,
    PhysicsSimulator,
    ScreeningFlag,
    SlopeInput,
    TemperatureInterval,
    TerramechanicsInput,
    TrackContact,
    WeatherLimits,
    WeatherSample,
    WeatherStopCondition,
    bounded_fraction,
    calculate_bearing,
    calculate_buoyancy,
    calculate_concrete_curing,
    calculate_slope,
    calculate_terramechanics,
    checked_divide,
    derate_weather,
    evaluate_physics,
    load_physics_input,
    parse_physics_input,
    physics_result_json,
    write_physics_result,
)
from open_construction_equipment.cad_blender import (
    ARTIFACT_FILENAMES,
    BoxBody,
    CadBodyKind,
    CadExporter,
    PhysicsBodyMode,
    cad_export_result_json,
    export_scene,
    export_wavefront,
    external_tool_report,
    generate_blender_python,
    generate_freecad_python,
    generate_mujoco_mjcf,
    generate_openscad,
    load_cad_scene,
    mesh_box,
    parse_cad_scene,
    write_cad_export_result,
)

ROOT = Path(__file__).resolve().parents[1]
PHYSICS_PATH = ROOT / "examples/physics/synthetic-physics.json"
CAD_PATH = ROOT / "examples/cad/synthetic-scene.json"
PHYSICS_SCHEMA = ROOT / "schemas/physics-input.schema.json"
CAD_SCHEMA = ROOT / "schemas/cad-scene.schema.json"


class PhysicsTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(PHYSICS_PATH.read_text(encoding="utf-8"))
        self.model = parse_physics_input(copy.deepcopy(self.data))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def flat_track(self, **changes):
        values = dict(
            track=TrackContact(2.0, 0.5, 10000.0),
            soil_cohesion_kpa=2.0,
            soil_friction_angle_rad=math.radians(30),
            soil_stiffness_kpa_per_m=500.0,
            rolling_resistance_coefficient=0.1,
            traction_efficiency=0.8,
            slope_angle_rad=0.0,
            maximum_modeled_sinkage_m=0.05,
        )
        values.update(changes)
        return TerramechanicsInput(**values)

    def test_terramechanics_hand_arithmetic_and_margin(self):
        result = calculate_terramechanics(self.flat_track())
        shear = 2 + 10 * math.tan(math.radians(30))
        self.assertAlmostEqual(result.contact_pressure_kpa, 10.0)
        self.assertAlmostEqual(result.sinkage_m, 0.02)
        self.assertAlmostEqual(result.maximum_shear_stress_kpa, shear)
        self.assertAlmostEqual(result.available_thrust_n, 1600 * shear)
        self.assertAlmostEqual(result.rolling_resistance_n, 2000)
        self.assertEqual(result.grade_resistance_n, 0)
        self.assertAlmostEqual(result.net_tractive_margin_n, 1600 * shear - 2000)
        self.assertIs(result.sinkage_flag, ScreeningFlag.WITHIN_MODEL_ASSUMPTION)

    def test_doubling_track_load_scales_pressure_sinkage_and_dry_friction(self):
        dry = self.flat_track(soil_cohesion_kpa=0.0)
        first = calculate_terramechanics(dry)
        doubled = calculate_terramechanics(replace(
            dry, track=replace(dry.track, normal_load_n=2 * dry.track.normal_load_n)
        ))
        self.assertAlmostEqual(doubled.contact_pressure_kpa, 2 * first.contact_pressure_kpa)
        self.assertAlmostEqual(doubled.sinkage_m, 2 * first.sinkage_m)
        self.assertAlmostEqual(doubled.maximum_shear_stress_kpa, 2 * first.maximum_shear_stress_kpa)
        self.assertAlmostEqual(doubled.available_thrust_n, 2 * first.available_thrust_n)
        # Resistance terms also change; total margin is not incorrectly assumed to scale.
        self.assertAlmostEqual(doubled.net_tractive_margin_n,
                               doubled.available_thrust_n - doubled.rolling_resistance_n - doubled.grade_resistance_n)

    def test_uphill_resistance_signs_and_negative_margin_are_preserved(self):
        beta = math.radians(10)
        result = calculate_terramechanics(self.flat_track(slope_angle_rad=beta))
        self.assertAlmostEqual(result.rolling_resistance_n, 0.1 * 20000 * math.cos(beta))
        self.assertAlmostEqual(result.grade_resistance_n, 20000 * math.sin(beta))
        negative = calculate_terramechanics(self.flat_track(
            soil_cohesion_kpa=0, soil_friction_angle_rad=0, rolling_resistance_coefficient=2
        ))
        self.assertEqual(negative.available_thrust_n, 0)
        self.assertLess(negative.net_tractive_margin_n, 0)

    def test_sinkage_threshold_zero_and_equality(self):
        exceeded = calculate_terramechanics(self.flat_track(maximum_modeled_sinkage_m=0))
        self.assertIs(exceeded.sinkage_flag, ScreeningFlag.THRESHOLD_EXCEEDED)
        equal = calculate_terramechanics(self.flat_track(maximum_modeled_sinkage_m=0.02))
        self.assertIs(equal.sinkage_flag, ScreeningFlag.WITHIN_MODEL_ASSUMPTION)

    def test_terramechanics_function_boundary_rejects_invalid_direct_models(self):
        for model in (
            self.flat_track(track=TrackContact(0, 0.5, 1)),
            self.flat_track(traction_efficiency=0),
            self.flat_track(slope_angle_rad=math.pi / 2),
            self.flat_track(soil_stiffness_kpa_per_m=0),
            self.flat_track(soil_cohesion_kpa=float("nan")),
        ):
            with self.subTest(model=model), self.assertRaises(ConfigError):
                calculate_terramechanics(model)

    def test_bearing_known_rectangle_load_and_threshold_equality(self):
        model = BearingInput(2, 3, 60000, 50, 5)
        result = calculate_bearing(model)
        self.assertEqual(result.applied_pressure_kpa, 10)
        self.assertEqual(result.allowable_pressure_kpa, 50)
        self.assertEqual(result.factor_of_safety, 5)
        self.assertEqual(result.utilization, 0.2)
        self.assertIs(result.threshold_flag, ScreeningFlag.WITHIN_MODEL_ASSUMPTION)
        self.assertIs(calculate_bearing(replace(model, required_factor_of_safety=6)).threshold_flag,
                      ScreeningFlag.THRESHOLD_EXCEEDED)
        with self.assertRaises(ConfigError):
            calculate_bearing(replace(model, vertical_service_load_n=0))

    def slope_model(self, **changes):
        values = dict(slope_angle_rad=math.radians(20), cohesion_kpa=0,
                      friction_angle_rad=math.radians(30), soil_unit_weight_kn_m3=18,
                      vertical_slice_height_m=2, pore_pressure_ratio=0,
                      required_factor_of_safety=1)
        values.update(changes)
        return SlopeInput(**values)

    def test_slope_friction_only_cohesion_and_pore_pressure(self):
        model = self.slope_model()
        result = calculate_slope(model)
        self.assertAlmostEqual(result.factor_of_safety,
                               math.tan(model.friction_angle_rad) / math.tan(model.slope_angle_rad))
        cohesive = calculate_slope(replace(model, cohesion_kpa=3))
        self.assertGreater(cohesive.factor_of_safety, result.factor_of_safety)
        no_effective_friction = calculate_slope(replace(model, pore_pressure_ratio=1))
        self.assertEqual(no_effective_friction.resisting_stress_kpa, 0)
        self.assertEqual(no_effective_friction.factor_of_safety, 0)
        cohesive_pore = calculate_slope(replace(model, cohesion_kpa=3, pore_pressure_ratio=1))
        self.assertAlmostEqual(cohesive_pore.factor_of_safety, 3 / cohesive_pore.driving_stress_kpa)

    def test_slope_threshold_equality_and_large_finite_case(self):
        model = self.slope_model()
        factor = calculate_slope(model).factor_of_safety
        self.assertIs(calculate_slope(replace(model, required_factor_of_safety=factor)).threshold_flag,
                      ScreeningFlag.WITHIN_MODEL_ASSUMPTION)
        large = calculate_slope(self.slope_model(
            slope_angle_rad=math.pi / 2 - 1e-9, vertical_slice_height_m=1e6
        ))
        self.assertTrue(math.isfinite(large.factor_of_safety))
        with self.assertRaises(ConfigError):
            calculate_slope(self.slope_model(slope_angle_rad=math.pi / 2))

    def test_buoyancy_freshwater_threshold_and_additional_mass(self):
        below = calculate_buoyancy(BuoyancyInput(2, 1000, 1000, 1))
        self.assertAlmostEqual(below.uplift_n, 2 * 1000 * 9.80665)
        self.assertAlmostEqual(below.resisting_n, 1000 * 9.80665)
        self.assertEqual(below.factor_of_safety, 0.5)
        self.assertAlmostEqual(below.additional_resisting_mass_kg, 1000)
        self.assertIs(below.threshold_flag, ScreeningFlag.THRESHOLD_EXCEEDED)
        equal = calculate_buoyancy(BuoyancyInput(2, 2000, 1000, 1))
        self.assertEqual(equal.factor_of_safety, 1)
        self.assertEqual(equal.additional_resisting_mass_kg, 0)
        self.assertIs(equal.threshold_flag, ScreeningFlag.WITHIN_MODEL_ASSUMPTION)

    def test_buoyancy_zero_displacement_and_overflow(self):
        zero = calculate_buoyancy(BuoyancyInput(0, 0, 1000, 1.2))
        self.assertIsNone(zero.factor_of_safety)
        self.assertEqual(zero.additional_resisting_mass_kg, 0)
        self.assertIs(zero.threshold_flag, ScreeningFlag.NOT_APPLICABLE)
        self.assertNotIn("Infinity", physics_result_json(evaluate_physics(replace(
            self.model, buoyancy=BuoyancyInput(0, 0, 1000, 1.2)
        ))))
        with self.assertRaises(ConfigError):
            calculate_buoyancy(BuoyancyInput(1e308, 1, 1e308, 1))

    def test_curing_reference_temperature_and_activation_energy_independence(self):
        first = calculate_concrete_curing(ConcreteCuringInput(
            (TemperatureInterval(3, 20), TemperatureInterval(4.5, 20)), 0, 20, 40000, 7.5
        ))
        second = calculate_concrete_curing(ConcreteCuringInput(
            (TemperatureInterval(3, 20), TemperatureInterval(4.5, 20)), 0, 20, 80000, 7.5
        ))
        self.assertEqual(first.nurse_saul_maturity_c_h, 150)
        self.assertAlmostEqual(first.arrhenius_equivalent_age_h, 7.5)
        self.assertAlmostEqual(second.arrhenius_equivalent_age_h, 7.5)
        self.assertTrue(first.target_reached)

    def test_curing_negative_raw_maturity_and_zero_target_not_release(self):
        curing = ConcreteCuringInput((TemperatureInterval(2, -5),), 0, 20, 40000, 0)
        result = calculate_concrete_curing(curing)
        self.assertEqual(result.nurse_saul_maturity_c_h, -10)
        self.assertTrue(result.target_reached)
        physics = evaluate_physics(replace(self.model, curing=curing))
        self.assertTrue(physics.curing.target_reached)
        self.assertFalse(physics.construction_authorized)
        self.assertFalse(physics.operational_release)

    def test_curing_invalid_absolute_zero_empty_and_nonpositive_duration(self):
        for model in (
            ConcreteCuringInput((), 0, 20, 40000, 0),
            ConcreteCuringInput((TemperatureInterval(0, 20),), 0, 20, 40000, 0),
            ConcreteCuringInput((TemperatureInterval(1, -273.15),), 0, 20, 40000, 0),
            ConcreteCuringInput((TemperatureInterval(1, 20),), 0, -273.15, 40000, 0),
        ):
            with self.subTest(model=model), self.assertRaises(ConfigError):
                calculate_concrete_curing(model)
        data = copy.deepcopy(self.data)
        data["curing"]["intervals"] = []
        with self.assertRaises(ConfigError):
            parse_physics_input(data)

    def test_weather_sample_product_and_no_operational_verdict(self):
        result = derate_weather(self.model.weather, self.model.weather_limits)
        self.assertAlmostEqual(result.temperature_factor, 0.72)
        self.assertAlmostEqual(result.precipitation_factor, 0.8)
        self.assertAlmostEqual(result.wind_factor, 0.5)
        self.assertAlmostEqual(result.combined_available_fraction, 0.288)
        self.assertEqual(result.stop_conditions, ())
        serialized = physics_result_json(evaluate_physics(self.model))
        self.assertNotIn('"SAFE"', serialized)
        self.assertNotIn('"PASS"', serialized)

    def test_weather_stop_order_cold_cutoff_and_zero_maxima(self):
        limits = WeatherLimits(5, 25, 15, 0.2, 0, 0)
        all_stops = derate_weather(WeatherSample(-10, 1, 2), limits)
        self.assertEqual(all_stops.temperature_factor, 0)
        self.assertEqual(all_stops.precipitation_factor, 0)
        self.assertEqual(all_stops.wind_factor, 0)
        self.assertEqual(all_stops.combined_available_fraction, 0)
        self.assertEqual(all_stops.stop_conditions, (
            WeatherStopCondition.COLD_THRESHOLD,
            WeatherStopCondition.PRECIPITATION_THRESHOLD,
            WeatherStopCondition.WIND_THRESHOLD,
        ))
        hot = derate_weather(WeatherSample(50, 0, 0), limits)
        self.assertEqual(hot.temperature_factor, 0)
        self.assertEqual(hot.stop_conditions, (WeatherStopCondition.HOT_THRESHOLD,))
        calm = derate_weather(WeatherSample(20, 0, 0), limits)
        self.assertEqual(calm.combined_available_fraction, 1)

    def test_weather_threshold_equality_and_fraction_bounds(self):
        limits = WeatherLimits(5, 25, 15, 0.1, 10, 20)
        equality = derate_weather(WeatherSample(5, 10, 20), limits)
        self.assertEqual(equality.stop_conditions, ())
        self.assertEqual(equality.precipitation_factor, 0)
        self.assertEqual(equality.wind_factor, 0)
        with self.assertRaises(ConfigError):
            derate_weather(WeatherSample(0, -1, 0), limits)
        with self.assertRaises(ConfigError):
            derate_weather(WeatherSample(0, 0, 0), replace(limits, maximum_temperature_c=5))

    def test_checked_arithmetic_helpers(self):
        self.assertEqual(checked_divide(3, 2, "test"), 1.5)
        self.assertEqual(bounded_fraction(0, "test"), 0)
        self.assertEqual(bounded_fraction(1, "test"), 1)
        for numerator, denominator in ((1, 0), (1, float("inf")), (1e-300, 1e300)):
            with self.subTest(numerator=numerator, denominator=denominator), self.assertRaises(ConfigError):
                checked_divide(numerator, denominator, "test")
        for value in (-0.01, 1.01, float("nan"), True):
            with self.subTest(value=value), self.assertRaises(ConfigError):
                bounded_fraction(value, "test")

    def test_parser_rejects_unknown_missing_boolean_and_nonfinite(self):
        mutations = []
        unknown = copy.deepcopy(self.data); unknown["extra"] = 1; mutations.append(unknown)
        missing = copy.deepcopy(self.data); del missing["bearing"]; mutations.append(missing)
        boolean = copy.deepcopy(self.data); boolean["bearing"]["verticalServiceLoad_N"] = True; mutations.append(boolean)
        for value in (float("nan"), float("inf"), float("-inf"), 10**400):
            changed = copy.deepcopy(self.data)
            changed["bearing"]["verticalServiceLoad_N"] = value
            mutations.append(changed)
        for changed in mutations:
            with self.subTest(changed=changed.get("bearing")), self.assertRaises(ConfigError):
                parse_physics_input(changed)

    def test_loader_rejects_duplicate_and_nonstandard_json_numbers(self):
        duplicate = Path(self.temp.name) / "duplicate.json"
        duplicate.write_text('{"analysisId":"x","analysisId":"y"}', encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "duplicate JSON key"):
            load_physics_input(duplicate)
        nan = Path(self.temp.name) / "nan.json"
        nan.write_text('{"value":NaN}', encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "non-standard JSON"):
            load_physics_input(nan)
        huge = Path(self.temp.name) / "huge.json"
        changed = copy.deepcopy(self.data)
        changed["bearing"]["verticalServiceLoad_N"] = 10**400
        huge.write_text(json.dumps(changed), encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "finite number"):
            load_physics_input(huge)

    def test_provenance_cannot_claim_owner_site_or_physical_evidence(self):
        for key, value in (("aiAuthored", False), ("ownerSupplied", True),
                           ("siteSupplied", True), ("physicalValidationPerformed", True)):
            with self.subTest(key=key):
                data = copy.deepcopy(self.data)
                data["provenance"][key] = value
                with self.assertRaises(ConfigError):
                    parse_physics_input(data)
        data = copy.deepcopy(self.data)
        data["provenance"]["statement"] = " \t\n"
        with self.assertRaisesRegex(ConfigError, "non-empty string"):
            parse_physics_input(data)

    def test_gate_ids_are_required_unique_and_shaped(self):
        for gates in ([], ["PG-001", "PG-001"], ["bad"], ["PG-001", 2]):
            with self.subTest(gates=gates):
                data = copy.deepcopy(self.data)
                data["requiredHumanGateIds"] = gates
                with self.assertRaises(ConfigError):
                    parse_physics_input(data)

    def test_envelope_units_platform_scope_and_license_are_fixed(self):
        for key in ("schemaVersion", "platform", "scope", "unitSystem", "spdxLicenseIdentifier"):
            with self.subTest(key=key):
                data = copy.deepcopy(self.data)
                data[key] = "invalid"
                with self.assertRaises(ConfigError):
                    parse_physics_input(data)

    def test_result_serialization_status_and_atomic_output_content(self):
        result = PhysicsSimulator().run(self.model)
        self.assertIs(result.status, EvidenceStatus.SIMULATED_UNREVIEWED)
        self.assertEqual(result.unresolved_human_gate_ids, self.model.required_human_gate_ids)
        self.assertFalse(result.physical_validation_performed)
        self.assertFalse(result.construction_authorized)
        self.assertFalse(result.operational_release)
        text = physics_result_json(result)
        decoded = json.loads(text)
        self.assertEqual(decoded["bearing"]["appliedPressure_kPa"], result.bearing.applied_pressure_kpa)
        self.assertEqual(decoded["buoyancy"]["uplift_N"], result.buoyancy.uplift_n)
        self.assertEqual(decoded["curing"]["nurseSaulMaturity_C_h"], result.curing.nurse_saul_maturity_c_h)
        self.assertEqual(text, physics_result_json(evaluate_physics(load_physics_input(PHYSICS_PATH))))
        path = write_physics_result(result, Path(self.temp.name) / "nested")
        self.assertEqual(path.name, "result.json")
        self.assertEqual(path.read_bytes(), text.encode("utf-8"))
        self.assertTrue(path.read_bytes().endswith(b"\n"))

    def test_result_serializer_rejects_status_release_and_gate_mutations(self):
        result = evaluate_physics(self.model)
        mutations = (
            {"status": "REVIEWED"},
            {"physical_validation_performed": True},
            {"construction_authorized": True},
            {"operational_release": True},
            {"unresolved_human_gate_ids": ()},
        )
        for changes in mutations:
            with self.subTest(changes=changes), self.assertRaises(ConfigError):
                physics_result_json(replace(result, **changes))

    def test_models_are_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            self.model.analysis_id = "changed"
        with self.assertRaises(FrozenInstanceError):
            self.model.terramechanics.track.length_m = 3

    @unittest.skipUnless(importlib.util.find_spec("jsonschema"), "optional jsonschema is not installed")
    def test_physics_schema_validates_example_and_rejects_invalid(self):
        import jsonschema
        schema = json.loads(PHYSICS_SCHEMA.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(schema)
        validator.validate(self.data)
        invalid = copy.deepcopy(self.data)
        invalid["provenance"]["statement"] = " \n"
        self.assertFalse(validator.is_valid(invalid))
        invalid = copy.deepcopy(self.data)
        invalid["bearing"]["verticalServiceLoad_N"] = 0
        self.assertFalse(validator.is_valid(invalid))


class CadTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(CAD_PATH.read_text(encoding="utf-8"))
        self.scene = parse_cad_scene(copy.deepcopy(self.data))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def test_box_mesh_topology_outward_winding_and_yaw(self):
        body = BoxBody("test_box", CadBodyKind.ATTACHMENT,
                       self.scene.bodies[0].center_m.__class__(1, 2, 3),
                       self.scene.bodies[0].size_m.__class__(2, 4, 6), math.pi / 2,
                       10, PhysicsBodyMode.STATIC, "attachment_steel")
        mesh = mesh_box(body)
        self.assertEqual(len(mesh.vertices_m), 8)
        self.assertEqual(len(mesh.triangles), 12)
        # Local +x half-extent rotates to +y.
        self.assertAlmostEqual(mesh.vertices_m[1].x_m, 3)
        self.assertAlmostEqual(mesh.vertices_m[1].y_m, 3)
        self.assertAlmostEqual(mesh.vertices_m[1].z_m, 0)
        for triangle in mesh.triangles:
            self.assertEqual(len(set(triangle)), 3)
            self.assertTrue(all(0 <= index < 8 for index in triangle))
            a, b, c = (mesh.vertices_m[index] for index in triangle)
            ab = (b.x_m-a.x_m, b.y_m-a.y_m, b.z_m-a.z_m)
            ac = (c.x_m-a.x_m, c.y_m-a.y_m, c.z_m-a.z_m)
            normal = (ab[1]*ac[2]-ab[2]*ac[1], ab[2]*ac[0]-ab[0]*ac[2], ab[0]*ac[1]-ab[1]*ac[0])
            self.assertGreater(sum(component * component for component in normal), 0)
            center = tuple((a_axis+b_axis+c_axis)/3 for a_axis, b_axis, c_axis in zip(
                (a.x_m, a.y_m, a.z_m), (b.x_m, b.y_m, b.z_m), (c.x_m, c.y_m, c.z_m)))
            outward = (center[0]-1, center[1]-2, center[2]-3)
            self.assertGreater(sum(n*d for n, d in zip(normal, outward)), 0)

    def test_mesh_rejects_zero_extent_and_nonfinite_values(self):
        body = self.scene.bodies[0]
        for changed in (
            replace(body, size_m=replace(body.size_m, x_m=0)),
            replace(body, mass_kg=0),
            replace(body, yaw_rad=float("nan")),
        ):
            with self.subTest(changed=changed), self.assertRaises(ConfigError):
                mesh_box(changed)

    def test_wavefront_obj_indices_material_link_and_no_assets(self):
        obj, mtl = export_wavefront(self.scene)
        self.assertIn("mtllib scene.mtl\n", obj)
        self.assertNotIn("map_Kd", mtl)
        self.assertNotIn("http", obj + mtl)
        vertex_count = len([line for line in obj.splitlines() if line.startswith("v ")])
        self.assertEqual(vertex_count, 8 * len(self.scene.bodies))
        faces = [line.split()[1:] for line in obj.splitlines() if line.startswith("f ")]
        self.assertEqual(len(faces), 12 * len(self.scene.bodies))
        self.assertTrue(all(len(face) == 3 for face in faces))
        self.assertTrue(all(1 <= int(index) <= vertex_count for face in faces for index in face))
        object_names = [line[2:] for line in obj.splitlines() if line.startswith("o ")]
        self.assertEqual(object_names, [body.body_id for body in self.scene.bodies])
        material_names = [line.split()[1] for line in mtl.splitlines() if line.startswith("newmtl ")]
        self.assertEqual(material_names, [item.material_id for item in self.scene.materials])
        self.assertEqual(set(line.split()[1] for line in obj.splitlines() if line.startswith("usemtl ")),
                         set(material_names))
        for vertex in [line for line in obj.splitlines() if line.startswith("v ")]:
            self.assertTrue(all("." in value and len(value.split(".")[1]) == 6 for value in vertex.split()[1:]))

    def test_blender_source_compiles_with_version_animation_and_optional_save(self):
        source = generate_blender_python(self.scene)
        compile(source, "<generated-blender>", "exec")
        self.assertIn("4 <= bpy.app.version[0] < 5", source)
        self.assertIn('point.interpolation = interpolation', source)
        self.assertIn("1 + int(round(DURATION_S / TIMESTEP_S))", source)
        self.assertIn('os.environ.get("OCE_BLENDER_OUTPUT")', source)
        self.assertIn("bpy.ops.wm.save_mainfile", source)
        self.assertNotIn(str(ROOT), source)
        self.assertNotIn("datetime", source)
        self.assertEqual(source, generate_blender_python(self.scene))

    def test_blender_mesh_centroids_use_one_pose_transform(self):
        source = generate_blender_python(self.scene)
        assignments = {}
        for node in ast.parse(source).body:
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id in {"MESHES", "BODIES", "ANIMATION"}):
                assignments[node.targets[0].id] = ast.literal_eval(node.value)
        self.assertEqual(set(assignments), {"MESHES", "BODIES", "ANIMATION"})
        mesh = next(item for item in assignments["MESHES"] if item[0] == "machine_body")
        initial_location = dict(assignments["BODIES"])["machine_body"]
        final_key = max(
            (item for item in assignments["ANIMATION"] if item[0] == "machine_body"),
            key=lambda item: item[1],
        )
        vertices = mesh[4]
        local_centroid = tuple(math.fsum(vertex[axis] for vertex in vertices) / len(vertices) for axis in range(3))
        self.assertEqual(local_centroid, (0.0, 0.0, 0.0))

        def world_centroid(location, yaw):
            x, y, z = local_centroid
            cosine, sine = math.cos(yaw), math.sin(yaw)
            return (
                cosine * x - sine * y + location[0],
                sine * x + cosine * y + location[1],
                z + location[2],
            )

        body = next(item for item in self.scene.bodies if item.body_id == "machine_body")
        initial_target = (body.center_m.x_m, body.center_m.y_m, body.center_m.z_m)
        for location, yaw, target in (
            (initial_location, mesh[3], initial_target),
            (final_key[2], final_key[3], (-1.5, 0.0, 0.75)),
        ):
            with self.subTest(location=location, yaw=yaw):
                self.assertEqual(world_centroid(location, yaw), target)

    def test_mujoco_xml_ground_modes_joints_and_box_dimensions(self):
        source = generate_mujoco_mjcf(self.scene)
        root = ET.fromstring(source)
        self.assertEqual(root.tag, "mujoco")
        self.assertEqual(root.find("compiler").attrib["angle"], "radian")
        option = root.find("option")
        self.assertEqual(float(option.attrib["timestep"]), self.scene.physics.timestep_s)
        self.assertEqual([float(value) for value in option.attrib["gravity"].split()], [0, 0, -9.80665])
        ground = root.find(".//geom[@name='ground']")
        self.assertEqual(ground.attrib["type"], "plane")
        bodies = {body.attrib["name"]: body for body in root.findall(".//worldbody/body")}
        for expected in self.scene.bodies:
            actual = bodies[expected.body_id]
            freejoints = actual.findall("freejoint")
            if expected.physics_mode is PhysicsBodyMode.RIGID:
                self.assertEqual(len(freejoints), 1)
            else:
                self.assertEqual(freejoints, [])
            if expected.physics_mode is PhysicsBodyMode.KINEMATIC:
                self.assertEqual(actual.attrib.get("mocap"), "true")
            geom = actual.find("geom")
            self.assertEqual(geom.attrib["type"], "box")
            self.assertEqual([float(value) for value in geom.attrib["size"].split()],
                             [expected.size_m.x_m/2, expected.size_m.y_m/2, expected.size_m.z_m/2])
            self.assertEqual(float(actual.find("inertial").attrib["mass"]), expected.mass_kg)
        self.assertIn("animation machine_body", source)
        self.assertNotIn("<actuator", source)

    def test_openscad_balanced_delimiters_and_single_mm_conversion(self):
        source = generate_openscad(self.scene)
        for left, right in (("(", ")"), ("[", "]"), ("{", "}")):
            self.assertEqual(source.count(left), source.count(right))
        self.assertIn("terrain_size_mm = [20000, 16000, 300];", source)
        self.assertIn("machine_body_center_mm = [-3000, 0, 750];", source)
        self.assertIn("cube(size_mm, center=true)", source)
        self.assertNotIn("import", source)
        self.assertEqual(source, generate_openscad(self.scene))

    def test_freecad_compiles_in_mm_and_core_has_no_framework_import(self):
        source = generate_freecad_python(self.scene)
        compile(source, "<generated-freecad>", "exec")
        self.assertIn("Part::Box", source)
        self.assertIn("(20000.0, 16000.0, 300.0)", source)
        self.assertIn("OCEPhysicsMode", source)
        core = (ROOT / "src/open_construction_equipment/cad_blender.py").read_text(encoding="utf-8")
        self.assertNotIn("import bpy", core)
        self.assertNotIn("import FreeCAD", core)

    def test_parser_rejects_bad_references_duplicates_and_modes(self):
        mutations = []
        unknown_material = copy.deepcopy(self.data); unknown_material["bodies"][0]["materialId"] = "missing"; mutations.append(unknown_material)
        duplicate_body = copy.deepcopy(self.data); duplicate_body["bodies"].append(copy.deepcopy(duplicate_body["bodies"][0])); mutations.append(duplicate_body)
        duplicate_material = copy.deepcopy(self.data); duplicate_material["materials"].append(copy.deepcopy(duplicate_material["materials"][0])); mutations.append(duplicate_material)
        unknown_animation = copy.deepcopy(self.data); unknown_animation["animation"][0]["bodyId"] = "missing"; mutations.append(unknown_animation)
        static_animation = copy.deepcopy(self.data); static_animation["animation"][0]["bodyId"] = "terrain"; mutations.append(static_animation)
        bad_mode = copy.deepcopy(self.data); bad_mode["bodies"][0]["physicsMode"] = "DYNAMIC"; mutations.append(bad_mode)
        bad_id = copy.deepcopy(self.data); bad_id["bodies"][0]["bodyId"] = "Terrain-1"; mutations.append(bad_id)
        for changed in mutations:
            with self.subTest(changed=changed["bodies"][0]), self.assertRaises(ConfigError):
                parse_cad_scene(changed)

    def test_animation_chronology_start_and_duration(self):
        for mutate in (
            lambda data: data["animation"][0].update(time_s=1),
            lambda data: data["animation"][1].update(time_s=0),
            lambda data: data["animation"][1].update(time_s=5),
            lambda data: data["animation"].append(copy.deepcopy(data["animation"][0])),
        ):
            data = copy.deepcopy(self.data)
            mutate(data)
            with self.subTest(data=data["animation"]), self.assertRaises(ConfigError):
                parse_cad_scene(data)

    def test_required_machine_bunker_and_rigid_interior_exclusion(self):
        for index in (0, 1):
            data = copy.deepcopy(self.data)
            if index == 0:
                data["bodies"] = [body for body in data["bodies"] if body["kind"] != "MACHINE"]
                data["animation"] = []
            else:
                data["bodies"] = [body for body in data["bodies"] if body["kind"] != "BUNKER"]
            with self.subTest(index=index), self.assertRaises(ConfigError):
                parse_cad_scene(data)
        data = copy.deepcopy(self.data)
        crate = next(body for body in data["bodies"] if body["bodyId"] == "tool_crate")
        crate["center_m"] = {"x_m": 4, "y_m": 1, "z_m": 1.2}
        with self.assertRaisesRegex(ConfigError, "prohibited bunker"):
            parse_cad_scene(data)

    def test_gravity_color_and_private_location_keys_are_rejected(self):
        for key in ("latitude", "GPS", "streetAddress", "parcelId"):
            data = copy.deepcopy(self.data)
            data[key] = "synthetic forbidden input"
            with self.subTest(key=key), self.assertRaises(ConfigError):
                parse_cad_scene(data)
        data = copy.deepcopy(self.data)
        data["physics"]["gravity_mps2"]["x_m"] = 1
        with self.assertRaises(ConfigError):
            parse_cad_scene(data)
        data = copy.deepcopy(self.data)
        data["materials"][0]["diffuse"]["red"] = 1.1
        with self.assertRaises(ConfigError):
            parse_cad_scene(data)

    def test_export_manifest_hashes_exact_files_lf_and_determinism(self):
        first_dir = Path(self.temp.name) / "first"
        second_dir = Path(self.temp.name) / "second"
        first = CadExporter().export(self.scene, first_dir)
        second = export_scene(self.scene, second_dir)
        self.assertEqual(tuple(item.filename for item in first.artifacts), ARTIFACT_FILENAMES)
        self.assertEqual({path.name for path in first_dir.iterdir()}, set(ARTIFACT_FILENAMES))
        for artifact in first.artifacts:
            first_bytes = (first_dir / artifact.filename).read_bytes()
            second_bytes = (second_dir / artifact.filename).read_bytes()
            self.assertEqual(first_bytes, second_bytes)
            self.assertEqual(hashlib.sha256(first_bytes).hexdigest(), artifact.sha256)
            self.assertEqual(len(first_bytes), artifact.size_bytes)
            self.assertNotIn(b"\r\n", first_bytes)
        self.assertFalse(first.external_tool_execution_performed)
        self.assertFalse(first.physical_validation_performed)
        self.assertFalse(first.fabrication_release)
        manifest = cad_export_result_json(first)
        self.assertEqual(manifest, cad_export_result_json(second))
        result_path = write_cad_export_result(first, first_dir)
        self.assertEqual(result_path.read_bytes(), manifest.encode("utf-8"))
        self.assertEqual(json.loads(manifest)["status"], "SIMULATED_UNREVIEWED")
        self.assertNotIn("result.json", [item["filename"] for item in json.loads(manifest)["artifacts"]])

    def test_cad_result_serializer_rejects_status_execution_and_release_mutations(self):
        result = export_scene(self.scene, Path(self.temp.name) / "serializer")
        mutations = (
            {"status": "REVIEWED"},
            {"external_tool_execution_performed": True},
            {"physical_validation_performed": True},
            {"fabrication_release": True},
        )
        for changes in mutations:
            with self.subTest(changes=changes), self.assertRaises(ConfigError):
                cad_export_result_json(replace(result, **changes))

    def test_validation_failure_creates_no_output_and_symlinks_are_refused(self):
        output = Path(self.temp.name) / "must_not_exist"
        malformed = replace(self.scene, bodies=())
        with self.assertRaises(ConfigError):
            export_scene(malformed, output)
        self.assertFalse(output.exists())
        destination = Path(self.temp.name) / "linked"
        if hasattr(os, "symlink"):
            os.symlink(Path(self.temp.name), destination)
            with self.assertRaises(OSError):
                export_scene(self.scene, destination)

    def test_facades_and_external_discovery_do_not_execute_tools(self):
        facade = CadExporter()
        self.assertEqual(facade.wavefront(self.scene), export_wavefront(self.scene))
        self.assertEqual(facade.blender(self.scene), generate_blender_python(self.scene))
        self.assertEqual(facade.mujoco(self.scene), generate_mujoco_mjcf(self.scene))
        self.assertEqual(facade.openscad(self.scene), generate_openscad(self.scene))
        self.assertEqual(facade.freecad(self.scene), generate_freecad_python(self.scene))
        with mock.patch("open_construction_equipment.cad_blender.shutil.which", side_effect=lambda name: f"/hint/{name}") as which:
            report = external_tool_report()
        self.assertEqual(set(report), {"blender", "openscad", "freecadcmd", "python"})
        self.assertTrue(all(value.startswith("/hint/") for value in report.values()))
        self.assertGreaterEqual(which.call_count, 4)

    def test_scene_and_mesh_are_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            self.scene.scene_id = "changed"
        mesh = mesh_box(self.scene.bodies[0])
        with self.assertRaises(FrozenInstanceError):
            mesh.vertices_m = ()

    @unittest.skipUnless(importlib.util.find_spec("jsonschema"), "optional jsonschema is not installed")
    def test_cad_schema_validates_example_and_rejects_invalid(self):
        import jsonschema
        schema = json.loads(CAD_SCHEMA.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(schema)
        validator.validate(self.data)
        invalid = copy.deepcopy(self.data)
        invalid["sceneId"] = "INVALID ID"
        self.assertFalse(validator.is_valid(invalid))
        invalid = copy.deepcopy(self.data)
        invalid["physics"]["gravity_mps2"]["x_m"] = 1
        self.assertFalse(validator.is_valid(invalid))

    @unittest.skipUnless(
        os.environ.get("OCE_RUN_OPTIONAL_EXTERNAL_TESTS") == "1" and importlib.util.find_spec("mujoco"),
        "opt-in external tests and optional mujoco are required",
    )
    def test_optional_mujoco_load_and_short_step(self):
        import mujoco
        output = Path(self.temp.name) / "mujoco"
        export_scene(self.scene, output)
        model = mujoco.MjModel.from_xml_path(str(output / "ctl01_bunker_physics.xml"))
        data = mujoco.MjData(model)
        mujoco.mj_step(model, data)
        self.assertTrue(math.isfinite(data.time))
        self.assertGreater(data.time, 0)


if __name__ == "__main__":
    unittest.main()
