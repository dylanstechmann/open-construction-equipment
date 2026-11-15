# SPDX-License-Identifier: Apache-2.0
import math
import unittest

from open_construction_equipment.geometry import (
    Circle, Point, circle_in_polygon, is_simple_polygon, obstacle_clearance, path_length,
    point_in_polygon, point_segment_distance, polygon_edge_distance,
    segment_is_clear, segments_intersect, wrap_angle,
)


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.square = (Point(0, 0), Point(4, 0), Point(4, 4), Point(0, 4))

    def test_angle_wrap_is_half_open(self):
        self.assertAlmostEqual(wrap_angle(3 * math.pi), -math.pi)
        self.assertAlmostEqual(wrap_angle(-math.pi / 2), -math.pi / 2)
        with self.assertRaises(ValueError):
            wrap_angle(math.nan)

    def test_polygon_boundary_is_inside(self):
        self.assertTrue(point_in_polygon(Point(0, 2), self.square))
        self.assertTrue(point_in_polygon(Point(2, 2), self.square))
        self.assertFalse(point_in_polygon(Point(5, 2), self.square))

    def test_circle_footprint_uses_all_edges(self):
        self.assertTrue(circle_in_polygon(Point(2, 2), 2.0, self.square))
        self.assertFalse(circle_in_polygon(Point(0.5, 2), 0.6, self.square))
        self.assertFalse(circle_in_polygon(Point(-1, 2), 0.1, self.square))
        self.assertAlmostEqual(polygon_edge_distance(Point(2, 2), self.square), 2.0)

    def test_segment_distance_and_intersection_include_endpoints(self):
        self.assertAlmostEqual(point_segment_distance(Point(1, 1), Point(0, 0), Point(2, 0)), 1.0)
        self.assertAlmostEqual(point_segment_distance(Point(3, 0), Point(0, 0), Point(2, 0)), 1.0)
        self.assertTrue(segments_intersect(Point(0, 0), Point(2, 2), Point(0, 2), Point(2, 0)))
        self.assertTrue(segments_intersect(Point(0, 0), Point(1, 0), Point(1, 0), Point(2, 0)))
        self.assertFalse(segments_intersect(Point(0, 0), Point(1, 0), Point(2, 1), Point(3, 1)))

    def test_signed_obstacle_clearance(self):
        obstacles = (Circle(Point(2, 2), 0.5),)
        self.assertAlmostEqual(obstacle_clearance(Point(2, 4), 0.25, obstacles), 1.25)
        self.assertLess(obstacle_clearance(Point(2, 2), 0.25, obstacles), 0)
        self.assertTrue(math.isinf(obstacle_clearance(Point(0, 0), 1, ())))

    def test_simple_polygon_allows_concave_but_rejects_self_contact(self):
        concave = (Point(0, 0), Point(4, 0), Point(4, 4), Point(2, 2), Point(0, 4))
        self.assertTrue(is_simple_polygon(concave))
        bowtie = (Point(0, 0), Point(4, 4), Point(0, 4), Point(4, 0))
        self.assertFalse(is_simple_polygon(bowtie))
        touching = (Point(0, 0), Point(4, 0), Point(4, 4), Point(1, 0), Point(0, 4))
        self.assertFalse(is_simple_polygon(touching))

    def test_swept_segment_checks_obstacles_and_concave_fence(self):
        obstacle = Circle(Point(4, 4), 0.1)
        fence = (Point(0, 0), Point(12, 0), Point(12, 12), Point(0, 12))
        self.assertFalse(segment_is_clear(Point(2, 2), Point(10, 10), 1.54, fence, (obstacle,)))
        self.assertTrue(segment_is_clear(Point(2, 2), Point(2, 10), 1.54, fence, (obstacle,)))
        concave = (Point(0, 0), Point(4, 0), Point(4, 4), Point(2, 2), Point(0, 4))
        self.assertFalse(segment_is_clear(Point(1, 3), Point(3, 3), 0.0, concave))

    def test_path_length(self):
        self.assertEqual(path_length([Point(0, 0), Point(3, 4), Point(3, 8)]), 9.0)


if __name__ == "__main__":
    unittest.main()
