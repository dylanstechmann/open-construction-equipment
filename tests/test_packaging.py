# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import tomllib
import unittest

from open_construction_equipment.resources import default_data_root
from open_construction_equipment.validation import repository_root

ROOT = repository_root()


class PackagingTests(unittest.TestCase):
    def test_source_checkout_uses_canonical_runtime_data(self):
        self.assertEqual(default_data_root(), ROOT)
        self.assertTrue((ROOT / "configs/ctl01.simulation.json").is_file())

    def test_modern_license_and_offline_shared_data_metadata(self):
        with (ROOT / "pyproject.toml").open("rb") as handle:
            project = tomllib.load(handle)
        self.assertIsInstance(project["project"]["license"], str)
        self.assertEqual(project["project"]["license"], "Apache-2.0")
        self.assertIn("NOTICE.md", project["project"]["license-files"])
        self.assertIn("LICENSES/*.txt", project["project"]["license-files"])
        data_files = project["tool"]["setuptools"]["data-files"]
        self.assertIn("share/open-construction-equipment/configs", data_files)
        self.assertIn("share/open-construction-equipment/hardware/ctl01/bom", data_files)
        self.assertEqual(project["build-system"]["requires"], ["setuptools>=77"])

    def test_license_references_have_complete_local_targets(self):
        for relative in ("LICENSES/Apache-2.0.txt", "LICENSES/CERN-OHL-S-2.0.txt", "LICENSES/CC-BY-SA-4.0.txt"):
            path = ROOT / relative
            self.assertTrue(path.is_file())
            self.assertGreater(path.stat().st_size, 1000)
        self.assertNotIn("No software package is included", (ROOT / "LICENSE").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
