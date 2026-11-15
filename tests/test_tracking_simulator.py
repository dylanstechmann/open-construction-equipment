# SPDX-License-Identifier: Apache-2.0
import math
import unittest

from open_construction_equipment.config import load_simulation_config
from open_construction_equipment.geometry import Point
from open_construction_equipment.models import Command, Pose
from open_construction_equipment.simulator import KinematicSimulator
from open_construction_equipment.tracking import PurePursuitTracker
from open_construction_equipment.validation import repository_root

ROOT = repository_root()


class TrackingTests(unittest.TestCase):
    def setUp(self):
        self.config = load_simulation_config(ROOT / "configs/ctl01.simulation.json")
        self.tracker = PurePursuitTracker(self.config.tracker, self.config.limits)
        self.path = [Point(0, 0), Point(5, 0)]

    def test_straight_tracking_is_bounded(self):
        result = self.tracker.update(Pose(0, 0, 0), self.path)
        self.assertGreater(result.command.speed, 0)
        self.assertLessEqual(result.command.speed, self.config.limits.max_autonomy_speed_mps)
        self.assertAlmostEqual(result.command.yaw_rate, 0.0)

    def test_goal_tolerance_returns_zero(self):
        result = self.tracker.update(Pose(5.1, 0, 1.0), self.path)
        self.assertTrue(result.goal_reached)
        self.assertEqual(result.command, Command())

    def test_large_heading_error_rotates_without_translation(self):
        result = self.tracker.update(Pose(0, 0, math.pi), self.path)
        self.assertEqual(result.command.speed, 0.0)
        self.assertLess(abs(result.command.yaw_rate), self.config.limits.max_yaw_rate_rps + 1e-12)

    def test_exact_ninety_degree_errors_rotate_without_translation(self):
        for yaw in (-math.pi / 2.0, math.pi / 2.0):
            with self.subTest(yaw=yaw):
                result = self.tracker.update(Pose(0, 0, yaw), self.path)
                self.assertEqual(result.command.speed, 0.0)
                self.assertAlmostEqual(abs(result.command.yaw_rate), self.config.limits.max_yaw_rate_rps)
                self.assertGreater(abs(result.command.yaw_rate), 0.0)
                self.assertLessEqual(abs(result.command.yaw_rate), self.config.limits.max_yaw_rate_rps)

    def test_sharp_corner_lookahead_does_not_advance_prematurely(self):
        for direction in (-1, 1):
            with self.subTest(direction=direction):
                path = [Point(0, 0), Point(0, 3), Point(direction * 3, 3)]
                before = self.tracker.update(Pose(0, 0, math.pi / 2), path)
                self.assertAlmostEqual(before.target.x, 0.0)
                self.assertAlmostEqual(before.target.y, self.config.tracker.lookahead_m)
                self.assertGreater(before.command.speed, 0.0, "aligned current-segment travel remains allowed")
                approached = self.tracker.update(Pose(0, 2.8, math.pi / 2), path)
                self.assertEqual(approached.target.y, 3.0)
                self.assertEqual(math.copysign(1.0, approached.target.x), direction)
                self.assertGreater(abs(approached.target.x), 1.0)
                self.assertEqual(approached.command.speed, 0.0)

    def test_sharp_vertex_approach_reduces_speed(self):
        path = [Point(0, 0), Point(0, 3), Point(3, 3)]
        far = self.tracker.update(Pose(0, 1, math.pi / 2), path)
        near = self.tracker.update(Pose(0, 2.5, math.pi / 2), path)
        self.assertGreater(near.command.speed, 0.0)
        self.assertLess(near.command.speed, far.command.speed)

    def test_sharp_corners_make_progress_without_oscillation_and_reach_goal(self):
        for direction in (-1, 1):
            with self.subTest(direction=direction):
                simulator = KinematicSimulator(self.config, Pose(0, 0, 0))
                tracker = PurePursuitTracker(self.config.tracker, self.config.limits)
                path = [Point(0, 0), Point(0, 3), Point(direction * 3, 3)]
                poses = [simulator.pose]
                reached = False
                for _ in range(800):
                    tracking = tracker.update(simulator.pose, path)
                    if tracking.goal_reached:
                        reached = True
                        break
                    simulator.step(tracking.command)
                    poses.append(simulator.pose)
                self.assertTrue(reached, "corner tracking must not stick or oscillate indefinitely")
                self.assertLess(simulator.stamp, 30.0)
                driven = sum(math.hypot(b.x - a.x, b.y - a.y) for a, b in zip(poses, poses[1:]))
                self.assertLess(driven, 8.0, "detour/oscillation around a six-metre path must stay bounded")
                self.assertLessEqual(math.hypot(simulator.pose.x - path[-1].x, simulator.pose.y - path[-1].y),
                                     self.config.tracker.goal_tolerance_m)

    def test_one_point_path_requires_already_reached_goal(self):
        self.assertTrue(self.tracker.update(Pose(0, 0, 0), [Point(0, 0)]).goal_reached)
        with self.assertRaisesRegex(ValueError, "already reached"):
            self.tracker.update(Pose(0, 0, 0), [Point(5, 0)])

    def test_curvature_and_goal_approach_reduce_speed(self):
        straight = self.tracker.update(Pose(0, 0, 0), self.path)
        curved = self.tracker.update(Pose(0, 0, 0), [Point(0, 0), Point(2, 2)])
        near = self.tracker.update(Pose(4.6, 0, 0), self.path)
        self.assertLess(curved.command.speed, straight.command.speed)
        self.assertLess(near.command.speed, straight.command.speed)


class SimulatorTests(unittest.TestCase):
    def setUp(self):
        self.config = load_simulation_config(ROOT / "configs/ctl01.simulation.json")
        self.simulator = KinematicSimulator(self.config, Pose(0, 0, 0))

    def test_acceleration_speed_and_yaw_limits(self):
        telemetry = self.simulator.step(Command(100, 100))
        self.assertAlmostEqual(telemetry.speed, 0.06)
        self.assertAlmostEqual(telemetry.yaw_rate, 0.15)
        for _ in range(100):
            telemetry = self.simulator.step(Command(100, 100))
        self.assertLessEqual(telemetry.speed, 0.8)
        self.assertLessEqual(telemetry.yaw_rate, 0.9)

    def test_deceleration_and_stop(self):
        for _ in range(20):
            self.simulator.step(Command(0.8, 0))
        telemetry = self.simulator.step(Command())
        self.assertAlmostEqual(telemetry.speed, 0.72)
        for _ in range(20):
            telemetry = self.simulator.step(Command())
        self.assertEqual(telemetry.speed, 0.0)

    def test_reverse_acceleration_and_braking_use_correct_limits(self):
        telemetry = self.simulator.step(Command(-0.8, 0))
        self.assertAlmostEqual(telemetry.speed, -0.06)
        for _ in range(20):
            self.simulator.step(Command(-0.8, 0))
        telemetry = self.simulator.step(Command())
        self.assertAlmostEqual(telemetry.speed, -0.72)
        for _ in range(20):
            telemetry = self.simulator.step(Command())
        self.assertEqual(telemetry.speed, 0.0)

    def test_reversal_brakes_through_zero_before_reverse_acceleration(self):
        self.simulator.speed = 0.005
        telemetry = self.simulator.step(Command(-0.8, 0))
        self.assertEqual(telemetry.speed, 0.0, "one braking step must not jump through zero")
        telemetry = self.simulator.step(Command(-0.8, 0))
        self.assertAlmostEqual(telemetry.speed, -0.06)
        self.simulator.speed = -0.005
        telemetry = self.simulator.step(Command(0.8, 0))
        self.assertEqual(telemetry.speed, 0.0)
        telemetry = self.simulator.step(Command(0.8, 0))
        self.assertAlmostEqual(telemetry.speed, 0.06)

    def test_invalid_timestep_and_nonfinite_command_rejected(self):
        for dt in (0, -0.1, math.nan, 0.21):
            with self.subTest(dt=dt), self.assertRaises(ValueError):
                self.simulator.step(Command(), dt)
        with self.assertRaises(ValueError):
            self.simulator.step(Command(math.nan, 0))

    def test_energy_hours_and_determinism(self):
        other = KinematicSimulator(self.config, Pose(0, 0, 0))
        for _ in range(20):
            first = self.simulator.step(Command(0.5, 0.1))
            second = other.step(Command(0.5, 0.1))
        self.assertEqual(first, second)
        self.assertAlmostEqual(self.simulator.stamp, 2.0)
        self.assertAlmostEqual(self.simulator.operating_hours, 2.0 / 3600)
        self.assertGreater(self.simulator.energy_used_kwh, 0)
        self.assertLess(self.simulator.charge_fraction, 1.0)

    def test_arc_integration_changes_pose_finitely(self):
        for _ in range(10):
            telemetry = self.simulator.step(Command(0.5, 0.5))
        self.assertGreater(telemetry.pose.x, 0)
        self.assertGreater(telemetry.pose.y, 0)
        self.assertNotEqual(telemetry.pose.yaw, 0)
        self.assertTrue(all(math.isfinite(v) for v in (telemetry.pose.x, telemetry.pose.y, telemetry.pose.yaw)))


if __name__ == "__main__":
    unittest.main()
