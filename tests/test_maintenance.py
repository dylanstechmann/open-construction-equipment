# SPDX-License-Identifier: Apache-2.0
import copy
import json
import tempfile
import unittest
from pathlib import Path

from open_construction_equipment.config import ConfigError
from open_construction_equipment.maintenance import evaluate_maintenance, load_service_history, load_service_plan
from open_construction_equipment.validation import repository_root

ROOT = repository_root()


def plan_item(**overrides):
    item = {"serviceId": "SVC-003", "intervalHours": 50, "intervalDays": 30,
            "everyUse": False, "eventTriggers": ["impact"], "basis": "PROPOSED test"}
    item.update(overrides)
    return item


def history(**overrides):
    value = {"recordType": "OCE-CTL-01-service-history", "platform": "OCE-CTL-01",
             "syntheticNotice": "SYNTHETIC ONLY", "asOf": "2026-11-15T12:00:00Z",
             "operatingHours": 100.0, "useCount": 10,
             "completedServices": [{"serviceId": "SVC-003", "completedAt": "2026-11-01T12:00:00Z",
                                    "operatingHours": 60.0, "useCount": 8,
                                    "sourceRecordId": "SYNTHETIC-1", "recordStatus": "SYNTHETIC_NOT_EVIDENCE"}],
             "events": []}
    value.update(overrides)
    return value


class MaintenanceTests(unittest.TestCase):
    def evaluate(self, item=None, record=None):
        return evaluate_maintenance({"items": [item or plan_item()]}, record or history())["items"][0]

    def test_operating_hours_current_and_overdue(self):
        self.assertEqual(self.evaluate()["status"], "current")
        self.assertEqual(self.evaluate(record=history(operatingHours=110))["status"], "overdue")
        self.assertIn("OPERATING_HOURS_EXCEEDED", self.evaluate(record=history(operatingHours=111))["reasons"])

    def test_calendar_interval_uses_utc_dates(self):
        result = self.evaluate(record=history(asOf="2026-12-01T12:00:00Z"))
        self.assertEqual(result["status"], "overdue")
        self.assertIn("CALENDAR_INTERVAL_EXCEEDED", result["reasons"])
        self.assertEqual(result["calendarDueAt"], "2026-12-01T12:00:00Z")

    def test_every_use_requires_new_use_since_explicit_completion(self):
        item = plan_item(intervalHours=None, intervalDays=None, everyUse=True, eventTriggers=[])
        self.assertEqual(self.evaluate(item, history(useCount=8))["status"], "current")
        result = self.evaluate(item, history(useCount=9))
        self.assertEqual(result["status"], "due")
        self.assertIn("EVERY_USE", result["reasons"])

    def test_event_trigger_only_after_last_completion(self):
        old = {"eventType": "impact", "occurredAt": "2026-10-30T12:00:00Z", "operatingHours": 59, "useCount": 7}
        self.assertEqual(self.evaluate(record=history(events=[old]))["status"], "current")
        new = {"eventType": "impact", "occurredAt": "2026-11-02T12:00:00Z", "operatingHours": 70, "useCount": 9}
        result = self.evaluate(record=history(events=[new]))
        self.assertEqual(result["status"], "due")
        self.assertIn("EVENT_TRIGGER", result["reasons"])

    def test_missing_completion_is_never_invented(self):
        result = self.evaluate(record=history(completedServices=[], operatingHours=0, useCount=0))
        self.assertEqual(result["status"], "due")
        self.assertIn("NO_COMPLETION_RECORD", result["reasons"])
        self.assertIsNone(result["lastCompletion"])
        self.assertEqual(result["completionEvidenceStatus"], "MISSING")

    def test_repository_plan_links_all_schedule_ids(self):
        loaded = load_service_plan(ROOT / "maintenance/ctl01/service-intervals.json", {f"SVC-{i:03d}" for i in range(1, 21)})
        self.assertEqual(len(loaded["items"]), 20)
        report = evaluate_maintenance(loaded, load_service_history(ROOT / "examples/maintenance/synthetic-service-history.json"))
        self.assertEqual(report["summary"]["total"], 20)
        self.assertGreater(report["summary"]["overdue"] + report["summary"]["due"], 0)
        self.assertEqual(report["intervalStatus"], "PROPOSED_NOT_OEM_SCHEDULE")

    def test_unknown_service_id_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            path.write_text(json.dumps({"recordType": "OCE-CTL-01-service-interval-plan", "platform": "OCE-CTL-01",
                                        "intervalStatus": "PROPOSED_NOT_OEM_SCHEDULE", "items": [plan_item()]}), encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "unknown service ID"):
                load_service_plan(path, {"SVC-999"})

    def test_future_or_impossible_records_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            bad = history(completedServices=[dict(history()["completedServices"][0], operatingHours=1000)])
            path.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "counters exceed"):
                load_service_history(path)
            bad = history(events=[{"eventType": "impact", "occurredAt": "2027-01-01T00:00:00Z", "operatingHours": 100, "useCount": 10}])
            path.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "after history asOf"):
                load_service_history(path)

    def test_completion_then_event_decreasing_counters_rejected(self):
        decreasing = history(events=[{"eventType": "impact", "occurredAt": "2026-11-02T12:00:00Z",
                                     "operatingHours": 59, "useCount": 8}])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            path.write_text(json.dumps(decreasing), encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "non-monotonic operatingHours"):
                load_service_history(path)
        with self.assertRaisesRegex(ConfigError, "non-monotonic operatingHours"):
            evaluate_maintenance({"items": [plan_item()]}, decreasing)

    def test_event_then_completion_decreasing_counters_rejected(self):
        decreasing = history(events=[{"eventType": "impact", "occurredAt": "2026-10-30T12:00:00Z",
                                     "operatingHours": 70, "useCount": 7}])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            path.write_text(json.dumps(decreasing), encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "non-monotonic operatingHours"):
                load_service_history(path)

    def test_equal_and_increasing_chronology_is_valid(self):
        valid = history(events=[
            {"eventType": "impact", "occurredAt": "2026-11-03T12:00:00Z", "operatingHours": 70, "useCount": 9},
            {"eventType": "inspection", "occurredAt": "2026-11-02T12:00:00Z", "operatingHours": 60, "useCount": 8},
        ])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            path.write_text(json.dumps(valid), encoding="utf-8")
            loaded = load_service_history(path)
            self.assertEqual(len(loaded["events"]), 2)
        self.assertEqual(self.evaluate(record=valid)["status"], "due")

    def test_equal_timestamp_and_counters_are_valid(self):
        valid = history(events=[{"eventType": "inspection", "occurredAt": "2026-11-01T12:00:00Z",
                                 "operatingHours": 60, "useCount": 8}])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            path.write_text(json.dumps(valid), encoding="utf-8")
            load_service_history(path)

    def test_basis_is_required_at_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            path.write_text(json.dumps({"recordType": "OCE-CTL-01-service-interval-plan", "platform": "OCE-CTL-01",
                                        "intervalStatus": "PROPOSED_NOT_OEM_SCHEDULE",
                                        "items": [plan_item(basis="  ")]}), encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "basis"):
                load_service_plan(path)
        with self.assertRaisesRegex(ConfigError, "basis"):
            evaluate_maintenance({"items": [plan_item(basis=None)]}, history())

    def test_huge_interval_days_are_a_controlled_config_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            path.write_text(json.dumps({"recordType": "OCE-CTL-01-service-interval-plan", "platform": "OCE-CTL-01",
                                        "intervalStatus": "PROPOSED_NOT_OEM_SCHEDULE",
                                        "items": [plan_item(intervalDays=1e308)]}), encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "supported UTC"):
                load_service_plan(path)
        with self.assertRaisesRegex(ConfigError, "supported UTC"):
            evaluate_maintenance({"items": [plan_item(intervalDays=1e308)]}, history())

    def test_calendar_addition_overflow_is_a_controlled_config_error(self):
        at_max = history(asOf="9999-12-31T23:59:59Z")
        at_max["completedServices"][0]["completedAt"] = "9999-12-31T23:59:59Z"
        with self.assertRaisesRegex(ConfigError, "valid UTC due timestamp"):
            evaluate_maintenance({"items": [plan_item(intervalDays=1)]}, at_max)

    def test_duplicate_completion_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            duplicate = history()
            duplicate["completedServices"] *= 2
            path.write_text(json.dumps(duplicate), encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "multiple completion"):
                load_service_history(path)


if __name__ == "__main__":
    unittest.main()
