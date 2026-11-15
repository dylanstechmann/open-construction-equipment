<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Proposed maintenance calculations

`maintenance/ctl01/service-intervals.json` links all existing `SVC-001` through `SVC-020` IDs from `service-schedule.csv`. It retains every-use and event-only entries. **Every interval is an initial AI-authored proposal with owner review pending, not an OEM, supplier, legal or released schedule.**

## Input records

The engine reads an `OCE-CTL-01-service-history` envelope containing:

- an explicit offset-aware `asOf` timestamp, current operating hours and use count;
- explicit completion records keyed by service ID, with completion timestamp/counters, source record ID and evidence status;
- explicit named events with timestamps/counters.

`examples/maintenance/synthetic-service-history.json` is entirely synthetic. `synthetic-service-003.json` and `synthetic-service-004.json` illustrate links to the controlled service-record template. No machine, maintenance, event, inspection, measurement or approval occurred. Empty/missing records are missing evidence, not successful service.

## Calculation

- Hour/calendar intervals compare current values with the last supplied completion. Equality at an interval is overdue for this conservative review tool.
- `everyUse` becomes due when the supplied use count increases since completion.
- A named event triggers an item only when it occurs after the last completion; without completion, any supplied matching event triggers it.
- Trigger/no-record items are `due`; exceeded hour/calendar items are `overdue`; otherwise items are `current`. Multiple reasons are retained.
- Output includes remaining hours and calendar due timestamp where computable. An item with no prior timed completion reports missing completion rather than fabricating an epoch.

Every plan item requires a nonempty `basis` rationale. Duplicate completions, unknown IDs, future records, naive timestamps and invalid values are rejected. Completions and events are sorted by timestamp with deterministic type/index ties; both operating hours and use count must be nondecreasing across the combined chronology, while equal values are valid. Direct evaluation applies the same history check, so due calculations cannot silently consume inconsistent records. Calendar intervals use checked UTC `datetime` arithmetic; intervals outside the supported date range or additions that overflow it are controlled input errors. The calculator does not create, approve or mark service complete and does not authorize return to service.

Run:

```sh
PYTHONPATH=src python3 -m open_construction_equipment maintenance --json
```

Any real future schedule must be derived from released design data, component suppliers, applicable law, risk assessment and approved responsible engineering review.
