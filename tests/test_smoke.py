from workforce_engine.models import AwardRule, ClockStatus, WorkSite


def test_workforce_models_defaults():
    site = WorkSite("SITE-AKL", "North Wharf", -36.842, 174.754, 200.0)
    rule = AwardRule("NZ-CONSTRUCTION-DEFAULT")
    assert site.radius_meters == 200.0
    assert rule.ordinary_daily_hours == 8.0
    assert ClockStatus.VERIFIED_ONSITE.value == "VERIFIED_ONSITE"
