# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from open_construction_equipment.config import load_mission_config, load_simulation_config
from open_construction_equipment.geometry import Circle, Point, circle_in_polygon, obstacle_clearance, segment_is_clear
from open_construction_equipment.mission import run_mission, trajectory_svg, write_mission_outputs
from open_construction_equipment.models import Pose
from open_construction_equipment.validation import repository_root

ROOT = repository_root()


class MissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_simulation_config(ROOT / "configs/ctl01.simulation.json")
        cls.mission = load_mission_config(ROOT / "examples/missions/synthetic-yard.json")

    def test_default_demo_succeeds_and_avoids_inflated_obstacles(self):
        result = run_mission(self.config, self.mission)
        self.assertEqual(result["status"], "succeeded", result["events"])
        self.assertLessEqual(result["metrics"]["finalGoalError_m"], self.config.tracker.goal_tolerance_m)
        self.assertGreater(result["metrics"]["drivenLength_m"], 10)
        for pose in result["actualPath"]:
            point = Point(pose["x_m"], pose["y_m"])
            self.assertTrue(circle_in_polygon(point, self.config.machine.footprint_radius_m, self.mission.geofence))
            self.assertGreaterEqual(obstacle_clearance(point, self.config.machine.footprint_radius_m + self.mission.safety_margin_m,
                                                       self.mission.obstacles), -1e-6)
        self.assertEqual(result["events"][-1]["reasons"], ["GOAL_REACHED"])

    def assert_coarse_detour_succeeds(self, yaw):
        fence = (Point(0, 0), Point(12, 0), Point(12, 12), Point(0, 12))
        obstacle = Circle(Point(4, 4), 0.1)
        mission = replace(self.mission, geofence=fence, obstacles=(obstacle,), start=Pose(2, 2, yaw),
                          goal=Pose(10, 10, 0), grid_resolution_m=4.0, max_duration_s=60.0)
        result = run_mission(self.config, mission)
        self.assertEqual(result["status"], "succeeded", result["events"])
        self.assertEqual(result["finalReasons"], ["GOAL_REACHED"])
        self.assertGreater(result["metrics"]["plannedLength_m"], Point(2, 2).distance(Point(10, 10)))
        planned = tuple(Point(item["x_m"], item["y_m"]) for item in result["plannedPath"])
        for start, end in zip(planned, planned[1:]):
            self.assertTrue(segment_is_clear(start, end, 1.54, fence, (obstacle,)))
        for pose in result["actualPath"]:
            point = Point(pose["x_m"], pose["y_m"])
            self.assertTrue(circle_in_polygon(point, self.config.machine.footprint_radius_m, fence))
            self.assertGreaterEqual(obstacle_clearance(point, 1.54, (obstacle,)), -1e-6)
        return result

    def test_original_coarse_grid_yaw_zero_mission_succeeds_without_safety_stop(self):
        result = self.assert_coarse_detour_succeeds(0.0)
        self.assertFalse(any("OBSTACLE_CLEARANCE" in event.get("reasons", []) for event in result["events"]))

    def test_coarse_grid_aligned_start_mission_also_succeeds(self):
        self.assert_coarse_detour_succeeds(1.5707963267948966)

    def test_exact_same_point_is_structured_immediate_success(self):
        mission = replace(self.mission, goal=self.mission.start, max_duration_s=0.05)
        result = run_mission(self.config, mission)
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["finalReasons"], ["GOAL_REACHED"])
        self.assertEqual(result["metrics"]["steps"], 0)
        self.assertEqual(result["metrics"]["duration_s"], 0.0)
        self.assertEqual(len(result["plannedPath"]), 1)

    def test_same_cell_distinct_points_track_without_error(self):
        mission = replace(self.mission, obstacles=(), start=Pose(2, 2, 0), goal=Pose(2.6, 2.6, 0),
                          grid_resolution_m=4.0, max_duration_s=10.0)
        result = run_mission(self.config, mission)
        self.assertEqual(result["status"], "succeeded", result["events"])
        self.assertEqual(len(result["plannedPath"]), 2)
        self.assertLessEqual(result["metrics"]["finalGoalError_m"], self.config.tracker.goal_tolerance_m)

    def test_exact_ninety_degree_initial_heading_turns_then_succeeds(self):
        mission = replace(self.mission, obstacles=(), start=Pose(2, 2, 1.5707963267948966),
                          goal=Pose(3.5, 2, 0), grid_resolution_m=4.0, max_duration_s=20.0)
        result = run_mission(self.config, mission)
        self.assertEqual(result["status"], "succeeded", result["events"])
        self.assertGreater(result["metrics"]["steps"], 1)

    def test_output_is_deterministic_and_self_contained(self):
        first, second = run_mission(self.config, self.mission), run_mission(self.config, self.mission)
        self.assertEqual(first, second)
        svg = trajectory_svg(first, self.mission)
        self.assertIn("SIMULATION ONLY", svg)
        self.assertIn("<svg", svg)
        self.assertNotIn("<image", svg)
        self.assertNotIn("href=", svg)
        with tempfile.TemporaryDirectory() as directory:
            a, b = Path(directory) / "a", Path(directory) / "b"
            write_mission_outputs(first, self.mission, a)
            write_mission_outputs(second, self.mission, b)
            self.assertEqual((a / "result.json").read_bytes(), (b / "result.json").read_bytes())
            self.assertEqual((a / "trajectory.svg").read_bytes(), (b / "trajectory.svg").read_bytes())
            parsed = json.loads((a / "result.json").read_text())
            self.assertTrue(parsed["simulationOnly"])

    def test_no_path_is_structured_not_hidden(self):
        obstacles = tuple(Circle(Point(8, y), 2.5) for y in (2, 6, 10))
        result = run_mission(self.config, replace(self.mission, obstacles=obstacles))
        self.assertEqual(result["status"], "no_path")
        self.assertEqual(result["finalReasons"], ["NO_PATH"])
        self.assertEqual(result["metrics"]["steps"], 0)
        self.assertEqual(result["events"][-1]["type"], "termination")

    def test_timeout_is_reported(self):
        result = run_mission(self.config, replace(self.mission, max_duration_s=0.2))
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(result["finalReasons"], ["TIMEOUT"])
        self.assertEqual(result["metrics"]["steps"], 2)

    def test_partial_final_step_never_exceeds_maximum_duration(self):
        result = run_mission(self.config, replace(self.mission, max_duration_s=0.25))
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(result["metrics"]["steps"], 3)
        self.assertAlmostEqual(result["metrics"]["duration_s"], 0.25)
        self.assertLessEqual(result["metrics"]["duration_s"], 0.25)

    def test_small_duration_uses_one_bounded_partial_step(self):
        result = run_mission(self.config, replace(self.mission, max_duration_s=0.05))
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(result["metrics"]["steps"], 1)
        self.assertAlmostEqual(result["metrics"]["duration_s"], 0.05)
        self.assertLessEqual(result["metrics"]["duration_s"], 0.05)


if __name__ == "__main__":
    unittest.main()
