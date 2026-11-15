# SPDX-License-Identifier: Apache-2.0
import math
import unittest

from open_construction_equipment.config import load_simulation_config
from open_construction_equipment.geometry import Circle, Point
from open_construction_equipment.models import Command, Pose, Telemetry
from open_construction_equipment.safety import Reason, SafetySupervisor, SupervisorState
from open_construction_equipment.validation import repository_root

ROOT = repository_root()


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.config = load_simulation_config(ROOT / "configs/ctl01.simulation.json")
        self.fence = (Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10))
        self.supervisor = self.make_supervisor()

    def make_supervisor(self, obstacles=()):
        return SafetySupervisor(self.config.limits, self.config.control, 0.5, self.fence, obstacles, 0.1)

    def telemetry(self, x=5.0, y=5.0, tilt=0.0):
        return Telemetry(1.0, Pose(x, y, 0.0), 0.0, 0.0, tilt)

    def update(self, command=Command(), **kwargs):
        values = dict(requested=command, telemetry=self.telemetry(), heartbeat_age=0.0, localization_age=0.0)
        values.update(kwargs)
        return self.supervisor.update(**values)

    def arm(self):
        decision = self.update(arm_request=True)
        self.assertEqual(decision.state, SupervisorState.ARMED)
        self.assertTrue(decision.command.is_zero())

    def test_boot_disabled_and_explicit_zero_arm(self):
        decision = self.update(Command(0.4, 0))
        self.assertEqual(decision.state, SupervisorState.DISABLED)
        self.assertEqual(decision.command, Command())
        decision = self.update(Command(0.4, 0), arm_request=True)
        self.assertIn(Reason.ARM_REQUIRES_ZERO, decision.reasons)
        self.arm()
        self.assertEqual(self.update(Command(0.4, 0.1)).command, Command(0.4, 0.1))

    def test_saturation_is_explicit_not_a_safety_fault(self):
        self.arm()
        decision = self.update(Command(100, -100))
        self.assertEqual(decision.state, SupervisorState.ARMED)
        self.assertEqual(decision.command, Command(0.8, -0.9))
        self.assertIn(Reason.COMMAND_SATURATED, decision.reasons)

    def test_estop_latches_without_auto_resume_and_reset_does_not_arm(self):
        self.arm()
        decision = self.update(Command(0.5, 0), estop=True)
        self.assertEqual(decision.state, SupervisorState.FAULT)
        self.assertEqual(decision.command, Command())
        self.assertEqual(decision.reasons[0], Reason.ESTOP)
        self.assertEqual(self.update(Command(0.5, 0)).state, SupervisorState.FAULT)
        decision = self.update(Command(0.1, 0), reset_request=True)
        self.assertIn(Reason.RESET_REQUIRES_ZERO, decision.reasons)
        decision = self.update(reset_request=True)
        self.assertEqual(decision.state, SupervisorState.DISABLED)
        self.assertEqual(self.update(Command(0.5, 0)).state, SupervisorState.DISABLED)
        self.arm()

    def test_reset_is_rejected_while_cause_is_active(self):
        self.arm()
        decision = self.update(reset_request=True, protective_fault=True)
        self.assertEqual(decision.state, SupervisorState.FAULT)
        self.assertIn(Reason.PROTECTIVE_FAULT, decision.reasons)

    def test_pause_and_manual_override_win_and_latch_stop(self):
        for flag, reason in (("pause", Reason.HUMAN_PAUSE), ("manual_override", Reason.MANUAL_OVERRIDE)):
            with self.subTest(flag=flag):
                self.supervisor = self.make_supervisor()
                self.arm()
                decision = self.update(Command(0.4, 0), **{flag: True})
                self.assertEqual(decision.state, SupervisorState.STOPPED)
                self.assertIn(reason, decision.reasons)
                self.assertEqual(self.update(Command(0.4, 0)).state, SupervisorState.STOPPED)
                self.assertEqual(self.update(reset_request=True).state, SupervisorState.DISABLED)

    def test_estop_has_priority_over_pause(self):
        self.arm()
        decision = self.update(estop=True, pause=True)
        self.assertEqual(decision.state, SupervisorState.FAULT)
        self.assertEqual(decision.reasons[0], Reason.ESTOP)
        self.assertIn(Reason.HUMAN_PAUSE, decision.reasons)

    def test_stale_heartbeat_and_localization_fault(self):
        for keyword in ("heartbeat_age", "localization_age"):
            with self.subTest(keyword=keyword):
                self.supervisor = self.make_supervisor()
                self.arm()
                decision = self.update(Command(0.4, 0), **{keyword: 0.31})
                expected = Reason.STALE_HEARTBEAT if keyword == "heartbeat_age" else Reason.STALE_LOCALIZATION
                self.assertEqual(decision.state, SupervisorState.FAULT)
                self.assertIn(expected, decision.reasons)
                self.assertEqual(self.update().state, SupervisorState.FAULT)

    def test_timeout_boundary_is_not_stale(self):
        self.arm()
        decision = self.update(Command(0.1, 0), heartbeat_age=0.3, localization_age=0.3)
        self.assertEqual(decision.state, SupervisorState.ARMED)

    def test_geofence_uses_full_footprint(self):
        self.arm()
        decision = self.update(telemetry=self.telemetry(x=0.4, y=5))
        self.assertEqual(decision.state, SupervisorState.FAULT)
        self.assertIn(Reason.GEOFENCE_VIOLATION, decision.reasons)

    def test_obstacle_clearance_uses_margin(self):
        self.supervisor = self.make_supervisor((Circle(Point(6, 5), 1.0),))
        decision = self.update(telemetry=self.telemetry(x=3, y=5), arm_request=True)
        self.assertEqual(decision.state, SupervisorState.ARMED)
        decision = self.update(telemetry=self.telemetry(x=4.45, y=5))
        self.assertEqual(decision.state, SupervisorState.FAULT)
        self.assertIn(Reason.OBSTACLE_CLEARANCE, decision.reasons)

    def test_tilt_limit_faults(self):
        self.arm()
        decision = self.update(telemetry=self.telemetry(tilt=self.config.limits.max_tilt_rad + 0.01))
        self.assertEqual(decision.state, SupervisorState.FAULT)
        self.assertIn(Reason.TILT_LIMIT, decision.reasons)

    def test_nonfinite_telemetry_command_and_age_fault(self):
        cases = [
            dict(telemetry=Telemetry(math.nan, Pose(5, 5, 0), 0, 0)),
            dict(telemetry=Telemetry(1, Pose(math.inf, 5, 0), 0, 0)),
            dict(requested=Command(math.nan, 0)),
            dict(heartbeat_age=math.inf),
        ]
        for overrides in cases:
            with self.subTest(overrides=overrides):
                self.supervisor = self.make_supervisor()
                self.arm()
                decision = self.update(**overrides)
                self.assertEqual(decision.state, SupervisorState.FAULT)
                self.assertEqual(decision.command, Command())


if __name__ == "__main__":
    unittest.main()
