# SPDX-License-Identifier: Apache-2.0
"""Due-item calculations from proposed intervals and supplied service history."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
from typing import Any

from .config import ConfigError, load_json

_MAX_INTERVAL_DAYS = (datetime.max.date() - datetime.min.date()).days


def _timestamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str):
        raise ConfigError(f"{name} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ConfigError(f"{name} is not a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ConfigError(f"{name} must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def _finite(value: Any, name: str, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{name} must be finite and >= {minimum}")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ConfigError(f"{name} must be finite and >= {minimum}") from exc
    if not math.isfinite(result) or result < minimum:
        raise ConfigError(f"{name} must be finite and >= {minimum}")
    return result


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{name} must be a non-empty string")
    return value


def _validate_plan(data: dict[str, Any], valid_service_ids: set[str] | None = None,
                   require_metadata: bool = True) -> dict[str, Any]:
    if require_metadata and (data.get("recordType") != "OCE-CTL-01-service-interval-plan" or
                             data.get("platform") != "OCE-CTL-01"):
        raise ConfigError("service plan recordType/platform is invalid")
    if require_metadata and data.get("intervalStatus") != "PROPOSED_NOT_OEM_SCHEDULE":
        raise ConfigError("service plan must remain PROPOSED_NOT_OEM_SCHEDULE")
    items = data.get("items")
    if not isinstance(items, list) or not items:
        raise ConfigError("service plan items must be a non-empty array")
    seen: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ConfigError(f"service plan item {index} must be an object")
        service_id = _identifier(item.get("serviceId"), f"items[{index}].serviceId")
        if service_id in seen:
            raise ConfigError(f"duplicate service plan ID {service_id}")
        if valid_service_ids is not None and service_id not in valid_service_ids:
            raise ConfigError(f"unknown service ID {service_id}")
        seen.add(service_id)
        hours, days = item.get("intervalHours"), item.get("intervalDays")
        if hours is not None:
            _finite(hours, f"{service_id}.intervalHours", 1e-9)
        if days is not None:
            finite_days = _finite(days, f"{service_id}.intervalDays", 1e-9)
            if finite_days > _MAX_INTERVAL_DAYS:
                raise ConfigError(f"{service_id}.intervalDays exceeds the supported UTC timestamp range")
        if not isinstance(item.get("everyUse"), bool):
            raise ConfigError(f"{service_id}.everyUse must be Boolean")
        events = item.get("eventTriggers")
        if not isinstance(events, list) or any(not isinstance(event, str) or not event for event in events):
            raise ConfigError(f"{service_id}.eventTriggers must be an array of names")
        _identifier(item.get("basis"), f"{service_id}.basis")
        if hours is None and days is None and not item["everyUse"] and not events:
            raise ConfigError(f"{service_id} needs at least one interval or trigger")
    return data


def load_service_plan(path: str | Path, valid_service_ids: set[str] | None = None) -> dict[str, Any]:
    return _validate_plan(load_json(path), valid_service_ids)


def _validate_history(data: dict[str, Any], valid_service_ids: set[str] | None = None) -> dict[str, Any]:
    if data.get("recordType") != "OCE-CTL-01-service-history" or data.get("platform") != "OCE-CTL-01":
        raise ConfigError("service history recordType/platform is invalid")
    as_of = _timestamp(data.get("asOf"), "asOf")
    _finite(data.get("operatingHours"), "operatingHours")
    _finite(data.get("useCount"), "useCount")
    completed = data.get("completedServices")
    if not isinstance(completed, list):
        raise ConfigError("completedServices must be an array")
    seen: set[str] = set()
    chronology: list[tuple[datetime, int, int, str, float, float]] = []
    for index, record in enumerate(completed):
        if not isinstance(record, dict):
            raise ConfigError(f"completedServices[{index}] must be an object")
        service_id = _identifier(record.get("serviceId"), f"completedServices[{index}].serviceId")
        if service_id in seen:
            raise ConfigError(f"multiple completion records for {service_id}; retain one explicit latest record")
        if valid_service_ids is not None and service_id not in valid_service_ids:
            raise ConfigError(f"unknown completed service ID {service_id}")
        seen.add(service_id)
        completed_at = _timestamp(record.get("completedAt"), f"{service_id}.completedAt")
        hours = _finite(record.get("operatingHours"), f"{service_id}.operatingHours")
        uses = _finite(record.get("useCount"), f"{service_id}.useCount")
        _identifier(record.get("sourceRecordId"), f"{service_id}.sourceRecordId")
        if record.get("recordStatus") not in ("SYNTHETIC_NOT_EVIDENCE", "RECORDED_UNREVIEWED", "REVIEWED"):
            raise ConfigError(f"{service_id}.recordStatus has unsupported evidence status")
        if completed_at > as_of:
            raise ConfigError(f"{service_id} completion is after history asOf")
        if hours > data["operatingHours"] or uses > data["useCount"]:
            raise ConfigError(f"{service_id} completion counters exceed current counters")
        chronology.append((completed_at, 0, index, f"completion {service_id}", hours, uses))
    events = data.get("events")
    if not isinstance(events, list):
        raise ConfigError("events must be an array")
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ConfigError(f"events[{index}] must be an object")
        _identifier(event.get("eventType"), f"events[{index}].eventType")
        occurred_at = _timestamp(event.get("occurredAt"), f"events[{index}].occurredAt")
        hours = _finite(event.get("operatingHours"), f"events[{index}].operatingHours")
        uses = _finite(event.get("useCount"), f"events[{index}].useCount")
        if occurred_at > as_of:
            raise ConfigError(f"events[{index}] occurs after history asOf")
        if hours > data["operatingHours"] or uses > data["useCount"]:
            raise ConfigError(f"events[{index}] counters exceed current counters")
        chronology.append((occurred_at, 1, index, f"event {index}", hours, uses))
    previous: tuple[datetime, int, int, str, float, float] | None = None
    for record in sorted(chronology, key=lambda item: item[:3]):
        if previous is not None:
            if record[4] < previous[4]:
                raise ConfigError(f"non-monotonic operatingHours: {record[3]} decreases from "
                                  f"{previous[4]} at {previous[3]} to {record[4]}")
            if record[5] < previous[5]:
                raise ConfigError(f"non-monotonic useCount: {record[3]} decreases from "
                                  f"{previous[5]} at {previous[3]} to {record[5]}")
        previous = record
    return data


def load_service_history(path: str | Path, valid_service_ids: set[str] | None = None) -> dict[str, Any]:
    return _validate_history(load_json(path), valid_service_ids)


def _calendar_due(completed_at: datetime, interval_days: Any, service_id: str) -> datetime:
    try:
        return completed_at + timedelta(days=_finite(interval_days, f"{service_id}.intervalDays", 1e-9))
    except (OverflowError, ValueError) as exc:
        raise ConfigError(f"{service_id}.intervalDays cannot produce a valid UTC due timestamp") from exc


def evaluate_maintenance(plan: dict[str, Any], history: dict[str, Any]) -> dict[str, Any]:
    """Return due state without creating, completing, or approving any service."""
    # Direct callers receive the same consistency checks as file/CLI callers.
    _validate_plan(plan, require_metadata=False)
    _validate_history(history)
    now = _timestamp(history["asOf"], "asOf")
    current_hours, current_uses = float(history["operatingHours"]), float(history["useCount"])
    completions = {item["serviceId"]: item for item in history["completedServices"]}
    results = []
    for item in plan["items"]:
        service_id = item["serviceId"]
        completion = completions.get(service_id)
        reasons: list[str] = []
        hours_remaining = None
        due_datetime = None
        if completion:
            completed_at = _timestamp(completion["completedAt"], f"{service_id}.completedAt")
            last_hours, last_uses = float(completion["operatingHours"]), float(completion["useCount"])
        else:
            completed_at, last_hours, last_uses = None, 0.0, 0.0
            if item["intervalHours"] is not None or item["intervalDays"] is not None:
                reasons.append("NO_COMPLETION_RECORD")
        if item["intervalHours"] is not None:
            hours_remaining = float(item["intervalHours"]) - (current_hours - last_hours)
            if hours_remaining <= 0:
                reasons.append("OPERATING_HOURS_EXCEEDED")
        if item["intervalDays"] is not None and completed_at is not None:
            due_datetime = _calendar_due(completed_at, item["intervalDays"], service_id)
            if now >= due_datetime:
                reasons.append("CALENDAR_INTERVAL_EXCEEDED")
        if item["everyUse"] and current_uses > last_uses:
            reasons.append("EVERY_USE")
        matching_events = [event for event in history["events"] if event["eventType"] in item["eventTriggers"]]
        if matching_events:
            if completed_at is None or any(_timestamp(event["occurredAt"], "event.occurredAt") > completed_at for event in matching_events):
                reasons.append("EVENT_TRIGGER")
        overdue_reasons = {"OPERATING_HOURS_EXCEEDED", "CALENDAR_INTERVAL_EXCEEDED"}
        status = "overdue" if overdue_reasons.intersection(reasons) else ("due" if reasons else "current")
        results.append({
            "serviceId": service_id,
            "status": status,
            "reasons": list(dict.fromkeys(reasons)),
            "lastCompletion": completion["completedAt"] if completion else None,
            "hoursRemaining": hours_remaining,
            "calendarDueAt": due_datetime.isoformat().replace("+00:00", "Z") if due_datetime is not None else None,
            "completionEvidenceStatus": completion["recordStatus"] if completion else "MISSING",
        })
    return {
        "schemaVersion": "1.0.0",
        "platform": "OCE-CTL-01",
        "intervalStatus": "PROPOSED_NOT_OEM_SCHEDULE",
        "historyNotice": history.get("syntheticNotice", "SUPPLIED_RECORDS_NOT_INDEPENDENTLY_VERIFIED"),
        "asOf": history["asOf"],
        "operatingHours": current_hours,
        "useCount": current_uses,
        "summary": {"total": len(results), "overdue": sum(row["status"] == "overdue" for row in results),
                    "due": sum(row["status"] == "due" for row in results),
                    "current": sum(row["status"] == "current" for row in results)},
        "items": results,
        "notice": "Calculations use only supplied completion records. No service is inferred, invented, approved, or marked complete.",
    }
