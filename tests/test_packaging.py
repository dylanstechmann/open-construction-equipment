# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import tomllib
import unittest

from open_construction_equipment import __version__
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
        self.assertIn("share/open-construction-equipment/examples/analysis", data_files)
        self.assertEqual(project["project"]["version"], "0.5.0")
        self.assertEqual(__version__, "0.5.0")
        self.assertEqual(project["project"]["dependencies"], [])
        self.assertEqual(project["project"]["optional-dependencies"], {
            "cad": ["cadquery>=2.5,<3"],
            "physics": ["mujoco>=3.2,<4"],
            "schema": ["jsonschema>=4.23,<5"],
        })
        expected_examples = {
            "physics": ["examples/physics/synthetic-physics.json"],
            "cad": ["examples/cad/synthetic-scene.json"],
            "powertrain": ["examples/powertrain/synthetic-microgrid.json"],
            "geohazard": ["examples/geohazard/synthetic-screen.json", "examples/geohazard/synthetic-adapt.json"],
            "economics": ["examples/economics/synthetic-pathways.json"],
        }
        for directory, sources in expected_examples.items():
            key = f"share/open-construction-equipment/examples/{directory}"
            self.assertEqual(data_files[key], sources)
            for source in sources:
                self.assertTrue((ROOT / source).is_file())
        self.assertEqual(project["build-system"]["requires"], ["setuptools>=77"])

    def test_license_references_have_complete_local_targets(self):
        for relative in ("LICENSES/Apache-2.0.txt", "LICENSES/CERN-OHL-S-2.0.txt", "LICENSES/CC-BY-SA-4.0.txt"):
            path = ROOT / relative
            self.assertTrue(path.is_file())
            self.assertGreater(path.stat().st_size, 1000)
        self.assertNotIn("No software package is included", (ROOT / "LICENSE").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
