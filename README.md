# Workforce Award & Compliance Engine

Multi-tenant workforce management rule engine providing ANZ Award/EBA pay interpretation, haversine geofenced attendance verification, fatigue compliance checks, and structured analytics for Workforce AI queries.

## Problem

Workforce platforms across construction, manufacturing, healthcare, and hospitality must transform raw clock-in events into payroll-accurate ordinary, overtime, weekend, and public-holiday hours while blocking spoofing or fatigue-breaching shifts.

## Solution

- **Geofence & Travel Integrity**: Verifies clock-in GPS coordinates against site boundaries and flags physically impossible travel speeds across consecutive punch events.
- **Award & EBA Interpretation**: Computes ordinary hours, `1.5x`/`2.0x` tiered overtime, public holiday multipliers, unpaid meal break deductions, and `< 10h` rest-gap fatigue flags.
- **Workforce AI Structured Queries**: Aggregates site job costing, overtime exposure, and compliance anomalies for safe, deterministic natural-language querying.

## Run Locally

```bash
python3 -m pip install -e ".[dev]"
pytest
```
