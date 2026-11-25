from datetime import datetime, timedelta, timezone

from workforce_engine.interpreter import WorkforceComplianceEngine, summarize_for_workforce_ai
from workforce_engine.models import AwardRule, ClockStatus, ShiftPunch, WorkSite


def _sites() -> dict[str, WorkSite]:
    return {
        "AKL-CBD": WorkSite("AKL-CBD", "Auckland CBD", -36.8485, 174.7633, radius_meters=150.0),
        "WLG-PORT": WorkSite("WLG-PORT", "Wellington Port", -41.2810, 174.7820, radius_meters=150.0),
    }


def test_geofence_verified_and_tiered_overtime_with_unpaid_break():
    engine = WorkforceComplianceEngine(_sites(), AwardRule("ANZ-STANDARD"))
    t0 = datetime(2026, 11, 24, 7, 0, tzinfo=timezone.utc)
    # 11.5h elapsed -> -0.5h break = 11.0 paid hours (8h @1.0 + 2h @1.5 + 1h @2.0 = 13.0x rate)
    punch = ShiftPunch(
        employee_id="emp-1",
        site_id="AKL-CBD",
        clock_in=t0,
        clock_out=t0 + timedelta(hours=11, minutes=30),
        in_lat=-36.8486,
        in_lon=174.7634,
        base_rate=40.0,
    )
    res = engine.interpret_shift(punch)
    assert res.clock_status == ClockStatus.VERIFIED_ONSITE
    assert res.paid_hours == 11.0
    assert (res.ordinary_hours, res.overtime_t1_hours, res.overtime_t2_hours) == (8.0, 2.0, 1.0)
    assert res.gross_pay == 520.0


def test_out_of_geofence_fatigue_breach_and_impossible_travel():
    engine = WorkforceComplianceEngine(_sites(), AwardRule("ANZ-STANDARD"))
    t0 = datetime(2026, 11, 24, 8, 0, tzinfo=timezone.utc)
    s1 = engine.interpret_shift(
        ShiftPunch("emp-2", "AKL-CBD", t0, t0 + timedelta(hours=4), -36.8485, 174.7633, 35.0)
    )
    assert s1.clock_status == ClockStatus.VERIFIED_ONSITE

    # 30 minutes later, clocks in from Wellington (~500km away!) -> impossible travel + fatigue breach
    s2 = engine.interpret_shift(
        ShiftPunch("emp-2", "WLG-PORT", t0 + timedelta(hours=4, minutes=30), t0 + timedelta(hours=8, minutes=30), -41.2810, 174.7820, 35.0, is_public_holiday=True)
    )
    assert s2.clock_status == ClockStatus.IMPOSSIBLE_TRAVEL
    assert any(f.startswith("FATIGUE_REST_BREACH") for f in s2.compliance_flags)
    assert any(f.startswith("IMPOSSIBLE_TRAVEL") for f in s2.compliance_flags)
    assert s2.gross_pay == 4 * 35.0 * 2.0


def test_workforce_ai_summary_aggregates_job_cost_and_anomalies():
    engine = WorkforceComplianceEngine(_sites(), AwardRule("ANZ-STANDARD"))
    t0 = datetime(2026, 11, 24, 8, 0, tzinfo=timezone.utc)
    r1 = engine.interpret_shift(ShiftPunch("emp-3", "AKL-CBD", t0, t0 + timedelta(hours=4), -36.8485, 174.7633, 50.0))
    r2 = engine.interpret_shift(ShiftPunch("emp-4", "AKL-CBD", t0, t0 + timedelta(hours=4), -36.8600, 174.7633, 50.0))
    summary = summarize_for_workforce_ai([r1, r2])
    assert summary.total_shifts == 2
    assert summary.unverified_clock_count == 1
    assert summary.job_cost_by_site == {"AKL-CBD": 400.0}
