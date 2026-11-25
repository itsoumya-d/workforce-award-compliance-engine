"""Geofenced clock-in verification, ANZ Award/EBA pay calculation, and AI query analytics."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List

from workforce_engine.models import (
    AwardRule,
    ClockStatus,
    InterpretedShift,
    ShiftPunch,
    WorkSite,
)


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance in meters between two WGS84 coordinates."""
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


@dataclass
class WorkforceAiSummary:
    total_shifts: int
    total_paid_hours: float
    total_gross_pay: float
    overtime_hours: float
    unverified_clock_count: int
    compliance_flag_count: int
    job_cost_by_site: Dict[str, float]


class WorkforceComplianceEngine:
    """Interprets workforce shift punches under ANZ award/EBA rules and geofence boundaries."""

    def __init__(self, sites: Dict[str, WorkSite], rule: AwardRule, max_travel_kmh: float = 180.0) -> None:
        self.sites = sites
        self.rule = rule
        self.max_travel_kmh = max_travel_kmh
        self._last_punch: Dict[str, ShiftPunch] = {}

    def interpret_shift(self, punch: ShiftPunch) -> InterpretedShift:
        site = self.sites[punch.site_id]
        dist_m = haversine_meters(punch.in_lat, punch.in_lon, site.lat, site.lon)
        flags: List[str] = []

        status = ClockStatus.VERIFIED_ONSITE if dist_m <= site.radius_meters else ClockStatus.OUT_OF_GEOFENCE
        if status == ClockStatus.OUT_OF_GEOFENCE:
            flags.append(f"OUT_OF_GEOFENCE:{int(round(dist_m))}m")

        prev = self._last_punch.get(punch.employee_id)
        if prev is not None:
            gap_hours = (punch.clock_in - prev.clock_out).total_seconds() / 3600.0
            if gap_hours < self.rule.min_rest_gap_hours:
                flags.append(f"FATIGUE_REST_BREACH:{gap_hours:.1f}h")
            elapsed_travel_h = max(1e-6, gap_hours)
            travel_km = haversine_meters(prev.in_lat, prev.in_lon, punch.in_lat, punch.in_lon) / 1000.0
            if travel_km / elapsed_travel_h > self.max_travel_kmh:
                status = ClockStatus.IMPOSSIBLE_TRAVEL
                flags.append(f"IMPOSSIBLE_TRAVEL:{int(travel_km / elapsed_travel_h)}kmh")
        self._last_punch[punch.employee_id] = punch

        raw_hours = max(0.0, (punch.clock_out - punch.clock_in).total_seconds() / 3600.0)
        break_deduct = (self.rule.unpaid_break_mins / 60.0) if raw_hours > self.rule.unpaid_break_threshold_hours else 0.0
        paid_hours = max(0.0, round(raw_hours - break_deduct, 2))

        if punch.is_public_holiday:
            ord_h, t1_h, t2_h = 0.0, 0.0, 0.0
            gross = paid_hours * punch.base_rate * self.rule.public_holiday_mult
            flags.append("PUBLIC_HOLIDAY_RATE")
        else:
            ord_h = min(paid_hours, self.rule.ordinary_daily_hours)
            rem = max(0.0, paid_hours - ord_h)
            t1_h = min(rem, self.rule.overtime_tier1_cap_hours)
            t2_h = max(0.0, rem - t1_h)
            gross = (
                ord_h * punch.base_rate
                + t1_h * punch.base_rate * self.rule.overtime_tier1_mult
                + t2_h * punch.base_rate * self.rule.overtime_tier2_mult
            )

        return InterpretedShift(
            employee_id=punch.employee_id,
            site_id=punch.site_id,
            clock_status=status,
            distance_meters=round(dist_m, 1),
            paid_hours=paid_hours,
            ordinary_hours=round(ord_h, 2),
            overtime_t1_hours=round(t1_h, 2),
            overtime_t2_hours=round(t2_h, 2),
            gross_pay=round(gross, 2),
            compliance_flags=flags,
        )


def summarize_for_workforce_ai(shifts: Iterable[InterpretedShift]) -> WorkforceAiSummary:
    """Aggregate structured job-costing, overtime, and compliance telemetry for AI queries."""
    items = list(shifts)
    by_site: Dict[str, float] = {}
    for s in items:
        by_site[s.site_id] = round(by_site.get(s.site_id, 0.0) + s.gross_pay, 2)

    return WorkforceAiSummary(
        total_shifts=len(items),
        total_paid_hours=round(sum(s.paid_hours for s in items), 2),
        total_gross_pay=round(sum(s.gross_pay for s in items), 2),
        overtime_hours=round(sum(s.overtime_t1_hours + s.overtime_t2_hours for s in items), 2),
        unverified_clock_count=sum(1 for s in items if s.clock_status != ClockStatus.VERIFIED_ONSITE),
        compliance_flag_count=sum(len(s.compliance_flags) for s in items),
        job_cost_by_site=by_site,
    )
