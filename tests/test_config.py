# SPDX-License-Identifier: Apache-2.0
import copy
import json
from pathlib import Path
import tempfile
import unittest

from open_construction_equipment.config import ConfigError, load_mission_config, load_simulation_config
from open_construction_equipment.validation import repository_root

ROOT = repository_root()


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.simulation = json.loads((ROOT / "configs/ctl01.simulation.json").read_text(encoding="utf-8"))
        self.mission = json.loads((ROOT / "examples/missions/synthetic-yard.json").read_text(encoding="utf-8"))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def write(self, data, mission=False):
        path = Path(self.temp.name) / ("mission.json" if mission else "config.json")
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_default_inputs_are_strictly_loaded(self):
        config = load_simulation_config(self.write(self.simulation))
        self.assertEqual(config.machine.mass_kg, 2200.0)
        self.assertAlmostEqual(config.limits.max_manual_speed_mps, 6 / 3.6)
        mission = load_mission_config(self.write(self.mission, True))
        self.assertEqual(len(mission.obstacles), 2)

    def test_unknown_and_missing_fields_are_rejected(self):
        self.simulation["machine"]["surprise"] = 1
        with self.assertRaisesRegex(ConfigError, "unknown fields"):
            load_simulation_config(self.write(self.simulation))
        self.simulation = json.loads((ROOT / "configs/ctl01.simulation.json").read_text())
        del self.simulation["control"]["period_s"]
        with self.assertRaisesRegex(ConfigError, "missing fields"):
            load_simulation_config(self.write(self.simulation))

    def test_nonfinite_boolean_and_negative_numbers_are_rejected(self):
        for value in (float("nan"), float("inf"), -1, True):
            with self.subTest(value=value):
                data = copy.deepcopy(self.simulation)
                data["machine"]["width_m"] = value
                with self.assertRaises(ConfigError):
                    load_simulation_config(self.write(data))

    def test_footprint_must_enclose_rectangle(self):
        self.simulation["machine"]["footprint_radius_m"] = 1.0
        with self.assertRaisesRegex(ConfigError, "must enclose"):
            load_simulation_config(self.write(self.simulation))

    def test_autonomy_cannot_exceed_manual_limit(self):
        self.simulation["limits"]["max_autonomy_speed_mps"] = 2.0
        with self.assertRaisesRegex(ConfigError, "cannot exceed"):
            load_simulation_config(self.write(self.simulation))

    def test_timeout_and_control_period_checks(self):
        self.simulation["control"]["heartbeat_timeout_s"] = 0.05
        with self.assertRaisesRegex(ConfigError, "at least one"):
            load_simulation_config(self.write(self.simulation))

    def test_simulation_only_cannot_be_disabled(self):
        self.simulation["simulationOnly"] = False
        with self.assertRaises(ConfigError):
            load_simulation_config(self.write(self.simulation))

    def test_mission_rejects_degenerate_and_outside_geometry(self):
        self.mission["geofence"] = [[0, 0], [1, 1], [2, 2]]
        with self.assertRaisesRegex(ConfigError, "non-zero area"):
            load_mission_config(self.write(self.mission, True))
        self.mission = json.loads((ROOT / "examples/missions/synthetic-yard.json").read_text())
        self.mission["goal"]["x_m"] = 100
        with self.assertRaisesRegex(ConfigError, "inside the geofence"):
            load_mission_config(self.write(self.mission, True))

    def test_duplicate_json_keys_are_rejected(self):
        path = Path(self.temp.name) / "duplicate.json"
        path.write_text('{"platform": "OCE-CTL-01", "platform": "other"}', encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "duplicate JSON key"):
            load_simulation_config(path)

    def test_self_intersecting_geofences_are_rejected(self):
        for fence in (
            [[0, 0], [4, 4], [0, 4], [4, 0]],
            [[0, 0], [4, 0], [0, 4], [4, 4], [0, 2]],
            [[0, 0], [4, 0], [4, 4], [1, 0], [0, 4]],
        ):
            with self.subTest(fence=fence):
                self.mission["geofence"] = fence
                with self.assertRaisesRegex(ConfigError, "non-self-intersecting"):
                    load_mission_config(self.write(self.mission, True))

    def test_valid_concave_geofence_is_accepted(self):
        self.mission["geofence"] = [[0, 0], [4, 0], [4, 4], [2, 2], [0, 4]]
        self.mission["obstacles"] = []
        self.mission["start"] = {"x_m": 1, "y_m": 1, "yaw_rad": 0}
        self.mission["goal"] = {"x_m": 3, "y_m": 1, "yaw_rad": 0}
        loaded = load_mission_config(self.write(self.mission, True))
        self.assertEqual(len(loaded.geofence), 5)

    def test_nonstandard_json_constants_are_rejected(self):
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                path = Path(self.temp.name) / "constant.json"
                path.write_text('{"machine": {"width_m": ' + constant + '}}', encoding="utf-8")
                with self.assertRaisesRegex(ConfigError, "non-standard JSON"):
                    load_simulation_config(path)

    def test_malformed_json_has_clear_error(self):
        path = Path(self.temp.name) / "broken.json"
        path.write_text("{broken", encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "cannot load"):
            load_simulation_config(path)


if __name__ == "__main__":
    unittest.main()
