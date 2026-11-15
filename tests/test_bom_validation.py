# SPDX-License-Identifier: Apache-2.0
import csv
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from open_construction_equipment.bom import read_bom, summarize_bom
from open_construction_equipment.validation import repository_root, validate_repository

ROOT = repository_root()


class BomTests(unittest.TestCase):
    def test_bom_totals_and_groups(self):
        report = summarize_bom(ROOT / "hardware/ctl01/bom/ctl01-bom.csv")
        self.assertEqual(report["itemCount"], 63)
        self.assertEqual(report["totalQuantity"], 70)
        self.assertIn("Structure", report["bySubsystem"])
        self.assertIn("yes", report["bySafetyCriticality"])
        self.assertEqual(report["bySafetyCriticality"]["yes"]["items"] + report["bySafetyCriticality"]["no"]["items"], 63)
        self.assertNotEqual(report["status"], "RELEASED")

    def test_duplicate_and_bad_quantity_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bom.csv"
            shutil.copyfile(ROOT / "hardware/ctl01/bom/ctl01-bom.csv", path)
            rows = list(csv.reader(path.read_text(encoding="utf-8").splitlines()))
            rows[1][3] = "0"
            path.write_text("\n".join(",".join(row) for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "positive"):
                read_bom(path)


class RepositoryValidationTests(unittest.TestCase):
    def test_current_repository_passes(self):
        report = validate_repository(ROOT)
        self.assertEqual(report["status"], "passed", report["errors"])
        self.assertFalse(report["physicalValidationPerformed"])
        self.assertGreaterEqual(report["jsonFilesChecked"], 10)

    def make_copy(self, directory):
        target = Path(directory)
        for name in ("configs", "examples", "hardware", "maintenance"):
            shutil.copytree(ROOT / name, target / name)
        shutil.copyfile(ROOT / "LICENSE", target / "LICENSE")
        return target

    def test_csv_width_and_procedure_cross_reference_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_copy(directory)
            schedule = root / "maintenance/ctl01/service-schedule.csv"
            with schedule.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            rows[0]["linked_procedure"] = "PR-999"
            with schedule.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            report = validate_repository(root)
            self.assertEqual(report["status"], "failed")
            self.assertTrue(any("PR-999" in error for error in report["errors"]))

    def test_csv_row_width_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_copy(directory)
            schedule = root / "maintenance/ctl01/service-schedule.csv"
            lines = schedule.read_text(encoding="utf-8").splitlines()
            lines[1] += ",extra"
            schedule.write_text("\n".join(lines) + "\n", encoding="utf-8")
            report = validate_repository(root)
            self.assertEqual(report["status"], "failed")
            self.assertTrue(any("columns" in error for error in report["errors"]))

    def test_duplicate_json_keys_and_nonstandard_constants_fail(self):
        for name, content in (
            ("duplicate", '{"recordType": "first", "recordType": "second"}'),
            ("nan", '{"value": NaN}'),
            ("infinity", '{"value": Infinity}'),
        ):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = self.make_copy(directory)
                (root / "configs/ctl01.simulation.json").write_text(content, encoding="utf-8")
                report = validate_repository(root)
                self.assertEqual(report["status"], "failed")
                expected = "duplicate JSON key" if name == "duplicate" else "non-standard JSON"
                self.assertTrue(any(expected in error for error in report["errors"]), report["errors"])

    def test_nonfinite_design_input_number_fails_semantic_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_copy(directory)
            path = root / "hardware/ctl01/design-inputs.json"
            path.write_text(path.read_text(encoding="utf-8").replace('"value": 2200', '"value": 1e999', 1), encoding="utf-8")
            report = validate_repository(root)
            self.assertEqual(report["status"], "failed")
            self.assertTrue(any("value must be finite" in error for error in report["errors"]), report["errors"])

    def test_unterminated_csv_fails_strict_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_copy(directory)
            path = root / "hardware/ctl01/bom/ctl01-bom.csv"
            path.write_text(path.read_text(encoding="utf-8") + '"unterminated,row\n', encoding="utf-8")
            report = validate_repository(root)
            self.assertEqual(report["status"], "failed")
            self.assertTrue(any("unexpected end of data" in error for error in report["errors"]), report["errors"])

    def test_stale_provenance_and_license_phrases_fail(self):
        mutations = (
            ("hardware/ctl01/cad/parameters.scad", "machine_width = 1500; // Owner concept target\n"),
            ("hardware/ctl01/interface-control.md", "These are owner-provided targets.\n"),
            ("LICENSE", "No software package is included in this phase.\n"),
        )
        for relative, content in mutations:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                root = self.make_copy(directory)
                path = root / relative
                path.write_text(path.read_text(encoding="utf-8") + content, encoding="utf-8")
                report = validate_repository(root)
                self.assertEqual(report["status"], "failed")
                self.assertTrue(any(relative in error for error in report["errors"]), report["errors"])

    def test_analysis_provenance_and_unknown_trace_fail_semantic_validation(self):
        for mutation in ("missing_provenance", "unknown_trace"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = self.make_copy(directory)
                path = root / "examples/analysis/synthetic-lc001.json"
                data = json.loads(path.read_text(encoding="utf-8"))
                if mutation == "missing_provenance":
                    del data["inputs"]["supports"]["frontX_m"]["provenance"]
                else:
                    data["inputs"]["machine"]["mass_kg"]["provenance"]["traceIds"] = ["DI-NOT-A-TRACE"]
                path.write_text(json.dumps(data), encoding="utf-8")
                report = validate_repository(root)
                self.assertEqual(report["status"], "failed")
                self.assertTrue(any("analysis input" in error for error in report["errors"]), report["errors"])

    def test_huge_analysis_integer_returns_failed_validation_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_copy(directory)
            path = root / "examples/analysis/synthetic-lc001.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["inputs"]["machine"]["mass_kg"]["value"] = 10**400
            path.write_text(json.dumps(data), encoding="utf-8")
            report = validate_repository(root)
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["analysisInputsChecked"], 0)
            self.assertTrue(
                any("analysis input" in error and "finite number" in error for error in report["errors"]),
                report["errors"],
            )

    def test_analysis_trace_must_exist_in_actual_source_registers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_copy(directory)
            path = root / "hardware/ctl01/safety/safety-requirements.csv"
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle, strict=True))
            for row in rows:
                if row["requirement_id"] == "SR-006":
                    row["requirement_id"] = "SR-RENAMED"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            report = validate_repository(root)
            self.assertEqual(report["status"], "failed")
            self.assertTrue(any("SR-006" in error and "source registers" in error for error in report["errors"]), report["errors"])

    def test_lc001_reference_remains_partial_unreviewed_and_tbd(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_copy(directory)
            path = root / "hardware/ctl01/mechanical/load-case-register.csv"
            content = path.read_text(encoding="utf-8").replace(
                "AN-LC-001A partial unreviewed synthetic static longitudinal only", "AN-LC-001A RELEASED"
            ).replace("Rigid body then multibody structural analysis,TBD,AN-LC-001A", "Rigid body then multibody structural analysis,CALCULATED,AN-LC-001A")
            path.write_text(content, encoding="utf-8")
            report = validate_repository(root)
            self.assertEqual(report["status"], "failed")
            self.assertTrue(any("analysis source traces" in error for error in report["errors"]), report["errors"])

    def test_malformed_json_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_copy(directory)
            (root / "configs/ctl01.simulation.json").write_text("{bad", encoding="utf-8")
            report = validate_repository(root)
            self.assertEqual(report["status"], "failed")
            self.assertTrue(report["errors"])


if __name__ == "__main__":
    unittest.main()
