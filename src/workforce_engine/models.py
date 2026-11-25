"""Core workforce site, award rule, clock-in, and payroll interpretation models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List


class ClockStatus(str, Enum):
    VERIFIED_ONSITE = "VERIFIED_ONSITE"
    OUT_OF_GEOFENCE = "OUT_OF_GEOFENCE"
    IMPOSSIBLE_TRAVEL = "IMPOSSIBLE_TRAVEL"


@dataclass
class WorkSite:
    site_id: str
    name: str
    lat: float
    lon: float
    radius_meters: float = 150.0


@dataclass
class AwardRule:
    award_id: str
    ordinary_daily_hours: float = 8.0
    overtime_tier1_cap_hours: float = 2.0
    overtime_tier1_mult: float = 1.5
    overtime_tier2_mult: float = 2.0
    public_holiday_mult: float = 2.0
    min_rest_gap_hours: float = 10.0
    unpaid_break_threshold_hours: float = 5.0
    unpaid_break_mins: int = 30


@dataclass
class ShiftPunch:
    employee_id: str
    site_id: str
    clock_in: datetime
    clock_out: datetime
    in_lat: float
    in_lon: float
    base_rate: float
    is_public_holiday: bool = False


@dataclass
class InterpretedShift:
    employee_id: str
    site_id: str
    clock_status: ClockStatus
    distance_meters: float
    paid_hours: float
    ordinary_hours: float
    overtime_t1_hours: float
    overtime_t2_hours: float
    gross_pay: float
    compliance_flags: List[str] = field(default_factory=list)
