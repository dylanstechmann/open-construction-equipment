# SPDX-License-Identifier: Apache-2.0
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

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
        for command in ("validate", "simulate", "maintenance", "bom"):
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
