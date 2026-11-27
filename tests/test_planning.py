# SPDX-License-Identifier: Apache-2.0
import unittest
from unittest.mock import patch

from open_construction_equipment.geometry import Circle, Point, obstacle_clearance, path_length, segment_is_clear
from open_construction_equipment.planning import NoPathError, OccupancyGrid, plan_path


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.fence = (Point(0, 0), Point(12, 0), Point(12, 10), Point(0, 10))

    def test_deterministic_eight_connected_plan(self):
        args = (self.fence, (Circle(Point(6, 5), 1.5),), Point(1, 1), Point(11, 9), 0.25, 0.5)
        first, second = plan_path(*args), plan_path(*args)
        self.assertEqual(first.path, second.path)
        self.assertGreater(len(first.path), 2)
        self.assertTrue(any(abs(a.x - b.x) > 0 and abs(a.y - b.y) > 0 for a, b in zip(first.path, first.path[1:])))

    def test_plan_respects_inflated_obstacles(self):
        obstacle = Circle(Point(6, 5), 1.5)
        result = plan_path(self.fence, (obstacle,), Point(1, 5), Point(11, 5), 0.25, 0.5)
        for waypoint in result.path:
            self.assertGreaterEqual(obstacle_clearance(waypoint, 0.5, (obstacle,)), -1e-9)
        for start, end in zip(result.path, result.path[1:]):
            self.assertTrue(segment_is_clear(start, end, 0.5, self.fence, (obstacle,)))

    def test_open_grid_with_off_center_endpoints(self):
        fence = (Point(0, 0), Point(3, 0), Point(3, 2), Point(0, 2))
        start, goal = Point(0.35, 0.55), Point(2.45, 1.6)
        distance = Point.distance
        goal_distances = 0

        def count_distance(point, other):
            nonlocal goal_distances
            if other is goal:
                goal_distances += 1
            return distance(point, other)

        with patch.object(Point, "distance", count_distance):
            plan = plan_path(fence, (), start, goal, resolution=0.5, inflation=0.1)

        # Several cell centers lie on the straight line between the exact endpoints.
        self.assertEqual((plan.path[0], plan.path[-1]), (start, goal))
        self.assertAlmostEqual(path_length(plan.path), start.distance(goal))
        # All 24 centers see the goal. A pairwise scan would take 24² distances.
        self.assertLessEqual(goal_distances, 2 * 24)

    def test_coarse_plan_checks_every_segment_and_exact_connectors(self):
        fence = (Point(0, 0), Point(12, 0), Point(12, 12), Point(0, 12))
        obstacle = Circle(Point(4, 4), 0.1)
        result = plan_path(fence, (obstacle,), Point(2, 2), Point(10, 10), 4.0, 1.54)
        self.assertNotEqual(result.path, (Point(2, 2), Point(6, 6), Point(10, 10)))
        self.assertGreater(len(result.path), 2)
        for start, end in zip(result.path, result.path[1:]):
            self.assertTrue(segment_is_clear(start, end, 1.54, fence, (obstacle,)),
                            f"colliding segment: {start} -> {end}")

    def test_exact_same_point_is_one_point_successful_plan(self):
        result = plan_path(self.fence, (), Point(2, 2), Point(2, 2), 4.0, 0.5)
        self.assertEqual(result.path, (Point(2, 2),))
        self.assertEqual(result.visited_cells, 0)

    def test_same_cell_distinct_points_return_safe_path_or_structured_error(self):
        clear = plan_path(self.fence, (), Point(2, 2), Point(2.6, 2.6), 4.0, 0.5)
        self.assertEqual(clear.path, (Point(2, 2), Point(2.6, 2.6)))
        obstacle = Circle(Point(2.25, 2.25), 0.1)
        try:
            detour = plan_path(self.fence, (obstacle,), Point(2, 2), Point(2.5, 2.5), 4.0, 0.1)
        except NoPathError as exc:
            self.assertEqual(exc.reason, "no_path")
        else:
            for start, end in zip(detour.path, detour.path[1:]):
                self.assertTrue(segment_is_clear(start, end, 0.1, self.fence, (obstacle,)))

    def test_no_path_when_inflated_obstacles_close_barrier(self):
        fence = (Point(0, 0), Point(20, 0), Point(20, 10), Point(0, 10))
        obstacles = tuple(Circle(Point(10, y), 2.0) for y in (2, 5, 8))
        with self.assertRaisesRegex(NoPathError, "no_path") as caught:
            plan_path(fence, obstacles, Point(2, 5), Point(18, 5), 0.25, 0.5)
        self.assertEqual(caught.exception.reason, "no_path")

    def test_blocked_start_and_goal_have_distinct_errors(self):
        obstacle = Circle(Point(1, 1), 1)
        with self.assertRaises(NoPathError) as caught:
            plan_path(self.fence, (obstacle,), Point(1, 1), Point(10, 8), 0.25, 0.5)
        self.assertEqual(caught.exception.reason, "start_blocked")
        with self.assertRaises(NoPathError) as caught:
            plan_path(self.fence, (obstacle,), Point(4, 4), Point(1, 1), 0.25, 0.5)
        self.assertEqual(caught.exception.reason, "goal_blocked")

    def test_diagonal_cannot_cut_between_blocked_cardinals(self):
        fence = (Point(0, 0), Point(4, 0), Point(4, 4), Point(0, 4))
        obstacles = (Circle(Point(1.5, 0.5), 0.45), Circle(Point(0.5, 1.5), 0.45))
        with self.assertRaises(NoPathError) as caught:
            plan_path(fence, obstacles, Point(0.5, 0.5), Point(1.5, 1.5), 1.0, 0.0)
        self.assertEqual(caught.exception.reason, "no_path", "the diagonal must not bypass two blocked cardinal cells")

    def test_grid_rejects_invalid_resolution(self):
        with self.assertRaises(ValueError):
            OccupancyGrid(self.fence, (), 0.0, 0.5)


if __name__ == "__main__":
    unittest.main()
