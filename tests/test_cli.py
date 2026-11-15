# SPDX-License-Identifier: Apache-2.0
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from open_construction_equipment.validation import repository_root

ROOT = repository_root()


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run([sys.executable, "-m", "open_construction_equipment", *map(str, args)],
                              cwd=ROOT, env=env, text=True, capture_output=True, timeout=30, check=False)

    def test_help_names_host_only_commands(self):
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        for command in ("validate", "simulate", "maintenance", "bom", "analyze", "bunker",
                        "physics", "export-cad", "powertrain", "site", "economics"):
            self.assertIn(command, result.stdout)
        self.assertIn("SIMULATION-ONLY", result.stdout)

    def test_validate_json_success(self):
        result = self.run_cli("validate", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "passed")

    def test_simulate_json_and_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_cli("simulate", "--json", "--output-dir", directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "succeeded")
            self.assertTrue((Path(directory) / "result.json").is_file())
            self.assertTrue((Path(directory) / "trajectory.svg").is_file())

    def test_maintenance_and_bom_json(self):
        maintenance = self.run_cli("maintenance", "--json")
        self.assertEqual(maintenance.returncode, 0, maintenance.stderr)
        self.assertEqual(json.loads(maintenance.stdout)["summary"]["total"], 20)
        bom = self.run_cli("bom", "--json")
        self.assertEqual(bom.returncode, 0, bom.stderr)
        self.assertEqual(json.loads(bom.stdout)["itemCount"], 63)

    def test_analyze_json_and_deterministic_report(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_cli("analyze", "--json", "--output-dir", directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["analysisId"], "AN-LC-001A")
            self.assertEqual(report["acceptanceStatus"], "NOT_ASSESSED")
            self.assertEqual(report["reviewStatus"], "UNREVIEWED")
            self.assertFalse(report["physicalValidationPerformed"])
            result_path = Path(directory) / "result.json"
            self.assertTrue(result_path.is_file())
            self.assertEqual(result_path.read_text(encoding="utf-8"), result.stdout)

    def test_version_is_v050(self):
        result = self.run_cli("--version")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "oce 0.5.0 (simulation/calculation-only)")

    def test_physics_powertrain_and_economics_write_matching_results(self):
        cases = (
            ("physics", "AN-PHYS-001"),
            ("powertrain", "AN-PWR-001"),
            ("economics", "AN-ECON-001"),
        )
        with tempfile.TemporaryDirectory() as directory:
            for command, analysis_id in cases:
                with self.subTest(command=command):
                    output = Path(directory) / command
                    result = self.run_cli(command, "--output-dir", output, "--json")
                    self.assertEqual(result.returncode, 0, result.stderr)
                    report = json.loads(result.stdout)
                    self.assertEqual(report["analysisId"], analysis_id)
                    self.assertEqual(report["status"], "SIMULATED_UNREVIEWED")
                    self.assertFalse(report["physicalValidationPerformed"])
                    self.assertEqual((output / "result.json").read_text(encoding="utf-8"), result.stdout)

    def test_export_cad_writes_six_artifacts_and_matching_manifest(self):
        names = (
            "scene.obj", "scene.mtl", "blender_scene.py", "ctl01_bunker_physics.xml",
            "scene.scad", "scene_freecad.py",
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            result = self.run_cli("export-cad", "--output-dir", output, "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads(result.stdout)
            self.assertEqual((output / "result.json").read_text(encoding="utf-8"), result.stdout)
            self.assertEqual(tuple(item["filename"] for item in manifest["artifacts"]), names)
            for artifact in manifest["artifacts"]:
                payload = (output / artifact["filename"]).read_bytes()
                self.assertEqual(len(payload), artifact["sizeBytes"])
                self.assertEqual(hashlib.sha256(payload).hexdigest(), artifact["sha256"])
            self.assertIn("mtllib scene.mtl\n", (output / "scene.obj").read_text(encoding="utf-8"))
            ET.fromstring((output / "ctl01_bunker_physics.xml").read_text(encoding="utf-8"))
            for name in ("blender_scene.py", "scene_freecad.py"):
                compile((output / name).read_text(encoding="utf-8"), name, "exec")
            self.assertFalse(manifest["externalToolExecutionPerformed"])
            self.assertFalse(manifest["fabricationRelease"])

    def test_site_screen_and_adapt_defaults_and_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            for mode in ("screen", "adapt"):
                with self.subTest(mode=mode):
                    output = Path(directory) / mode
                    result = self.run_cli("site", "--mode", mode, "--output-dir", output, "--json")
                    self.assertEqual(result.returncode, 0, result.stderr)
                    report = json.loads(result.stdout)
                    self.assertEqual(report["mode"], mode)
                    self.assertFalse(report["locationDataRetained"])
                    self.assertNotIn("verticesLocal", result.stdout)
                    self.assertTrue(all(gate["status"] == "UNRESOLVED" for gate in report["humanGates"]))
                    self.assertEqual((output / "result.json").read_text(encoding="utf-8"), result.stdout)

    def test_new_commands_reject_empty_input_without_output(self):
        commands = (
            ("physics",), ("export-cad",), ("powertrain",),
            ("site", "--mode", "screen"), ("site", "--mode", "adapt"), ("economics",),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.json"
            path.write_text("{}", encoding="utf-8")
            for index, command in enumerate(commands):
                with self.subTest(command=command):
                    output = Path(directory) / f"out-{index}"
                    result = self.run_cli(*command, "--input", path, "--output-dir", output, "--json")
                    self.assertEqual(result.returncode, 2)
                    self.assertIn("ERROR:", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertFalse(output.exists())

    def test_site_privacy_violations_fail_closed_without_output(self):
        for mode in ("screen", "adapt"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                source = ROOT / f"examples/geohazard/synthetic-{mode}.json"
                data = json.loads(source.read_text(encoding="utf-8"))
                data["latitude"] = 51.5
                path = Path(directory) / "private.json"
                path.write_text(json.dumps(data), encoding="utf-8")
                output = Path(directory) / "out"
                result = self.run_cli("site", "--mode", mode, "--input", path, "--output-dir", output, "--json")
                self.assertEqual(result.returncode, 2)
                self.assertIn("ERROR:", result.stderr)
                self.assertIn("private location", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse(output.exists())

    def test_new_commands_reject_huge_integers_without_output(self):
        cases = (
            (("physics",), "physics/synthetic-physics.json", ("bearing", "verticalServiceLoad_N")),
            (("export-cad",), "cad/synthetic-scene.json", ("physics", "timestep_s")),
            (("powertrain",), "powertrain/synthetic-microgrid.json", ("pv", "nameplate_kW")),
            (("site", "--mode", "screen"), "geohazard/synthetic-screen.json",
             ("candidates", 0, "factors", "karst", "closedDepressionDistance_m")),
            (("site", "--mode", "adapt"), "geohazard/synthetic-adapt.json", ("site", "baselineCost")),
            (("economics",), "economics/synthetic-pathways.json", ("annualFixedOwnershipCost",)),
        )
        with tempfile.TemporaryDirectory() as directory:
            for index, (command, relative, field_path) in enumerate(cases):
                with self.subTest(command=command):
                    data = json.loads((ROOT / "examples" / relative).read_text(encoding="utf-8"))
                    target = data
                    for key in field_path[:-1]:
                        target = target[key]
                    target[field_path[-1]] = 10**400
                    path = Path(directory) / f"huge-{index}.json"
                    path.write_text(json.dumps(data), encoding="utf-8")
                    output = Path(directory) / f"out-{index}"
                    result = self.run_cli(*command, "--input", path, "--output-dir", output, "--json")
                    self.assertEqual(result.returncode, 2)
                    self.assertIn("ERROR:", result.stderr)
                    self.assertIn("finite number", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertFalse(output.exists())

    def test_site_mode_mismatch_is_controlled_without_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "out"
            result = self.run_cli("site", "--mode", "adapt", "--input",
                                  ROOT / "examples/geohazard/synthetic-screen.json",
                                  "--output-dir", output, "--json")
            self.assertEqual(result.returncode, 2)
            self.assertIn("ERROR:", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse(output.exists())

    def test_invalid_analysis_returns_controlled_error_without_report(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad-analysis.json"
            path.write_text("{}", encoding="utf-8")
            output = Path(directory) / "out"
            result = self.run_cli("analyze", "--input", path, "--output-dir", output, "--json")
            self.assertEqual(result.returncode, 2)
            self.assertIn("ERROR:", result.stderr)
            self.assertIn("missing fields", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse(output.exists())

    def test_huge_analysis_integer_exits_two_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            data = json.loads((ROOT / "examples/analysis/synthetic-lc001.json").read_text(encoding="utf-8"))
            data["inputs"]["machine"]["mass_kg"]["value"] = 10**400
            path = Path(directory) / "huge-analysis.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            output = Path(directory) / "out"
            result = self.run_cli("analyze", "--input", path, "--output-dir", output, "--json")
            self.assertEqual(result.returncode, 2)
            self.assertIn("finite number", result.stderr)
            self.assertIn("ERROR:", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse(output.exists())

    def test_malformed_config_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{}", encoding="utf-8")
            result = self.run_cli("simulate", "--config", path, "--output-dir", Path(directory) / "out")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ERROR:", result.stderr)

    def test_no_path_returns_specific_failure_exit(self):
        mission = json.loads((ROOT / "examples/missions/synthetic-yard.json").read_text(encoding="utf-8"))
        mission["obstacles"] = [{"id": "BLOCK-GOAL", "center": [14, 10], "radius_m": 1.0}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "blocked.json"
            path.write_text(json.dumps(mission), encoding="utf-8")
            result = self.run_cli("simulate", "--mission", path, "--output-dir", Path(directory) / "out", "--json")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["status"], "no_path")

    def test_maintenance_overflow_is_controlled_input_error(self):
        plan = json.loads((ROOT / "maintenance/ctl01/service-intervals.json").read_text(encoding="utf-8"))
        plan["items"][0]["intervalDays"] = 1e308
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "overflow.json"
            path.write_text(json.dumps(plan), encoding="utf-8")
            result = self.run_cli("maintenance", "--plan", path)
            self.assertEqual(result.returncode, 2)
            self.assertIn("ERROR:", result.stderr)
            self.assertIn("supported UTC", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_unterminated_bom_csv_is_controlled_input_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text((ROOT / "hardware/ctl01/bom/ctl01-bom.csv").read_text(encoding="utf-8") + '"unterminated,row\n',
                            encoding="utf-8")
            result = self.run_cli("bom", "--bom", path)
            self.assertEqual(result.returncode, 2)
            self.assertIn("ERROR:", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_invalid_bom_returns_nonzero(self):
        result = self.run_cli("bom", "--bom", "does-not-exist.csv")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ERROR:", result.stderr)


if __name__ == "__main__":
    unittest.main()
