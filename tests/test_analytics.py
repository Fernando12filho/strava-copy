import pytest

from app import analytics


def _constant_pace_stream(total_km, seconds_per_km=300):
    times = [i * seconds_per_km for i in range(total_km + 1)]
    distances = [i * 1000.0 for i in range(total_km + 1)]
    return times, distances


# --- best_effort ---------------------------------------------------------

def test_best_effort_correct_5k_from_known_stream():
    times, distances = _constant_pace_stream(total_km=10, seconds_per_km=300)

    duration = analytics.best_effort(times, distances, target_distance_meters=5000)

    assert duration == pytest.approx(1500.0, abs=0.01)


def test_best_effort_activity_shorter_than_target_returns_none():
    times, distances = _constant_pace_stream(total_km=3, seconds_per_km=300)

    duration = analytics.best_effort(times, distances, target_distance_meters=5000)

    assert duration is None


def test_new_best_effort_replaces_old():
    assert analytics.is_new_best_effort(existing_seconds=1600, candidate_seconds=1500) is True


def test_non_pr_does_not_overwrite():
    assert analytics.is_new_best_effort(existing_seconds=1500, candidate_seconds=1600) is False
    assert analytics.is_new_best_effort(existing_seconds=None, candidate_seconds=1600) is True


# --- HR zones --------------------------------------------------------------

ZONES = [
    {"zone_number": 1, "min_bpm": 100, "max_bpm": 129},
    {"zone_number": 2, "min_bpm": 130, "max_bpm": 159},
    {"zone_number": 3, "min_bpm": 160, "max_bpm": 200},
]


def test_hr_zones_time_in_zone_sums_to_total_duration():
    times = [0, 60, 120, 180]
    hr_values = [110, 145, 170, 110]

    zone_seconds = analytics.time_in_zone(times, hr_values, ZONES)

    assert sum(zone_seconds.values()) == pytest.approx(180.0)


def test_hr_zones_sample_on_boundary_correct_zone():
    times = [0, 60, 120, 180]
    hr_values = [110, 130, 170, 110]

    zone_seconds = analytics.time_in_zone(times, hr_values, ZONES)

    assert zone_seconds[1] == pytest.approx(60.0)
    assert zone_seconds[2] == pytest.approx(60.0)
    assert zone_seconds[3] == pytest.approx(60.0)


# --- splits ------------------------------------------------------------

def test_splits_1km_correct_from_known_distance_stream():
    times, distances = _constant_pace_stream(total_km=10, seconds_per_km=300)

    splits = analytics.km_splits(times, distances, split_meters=1000)

    assert len(splits) == 10
    for split in splits:
        assert split["distance_meters"] == pytest.approx(1000.0)
        assert split["duration_seconds"] == pytest.approx(300.0)
        assert split["pace_per_km_seconds"] == pytest.approx(300.0)


def test_splits_partial_final_split_included():
    times = [0, 300, 600, 900, 1200, 1500, 1650]
    distances = [0, 1000, 2000, 3000, 4000, 5000, 5500]

    splits = analytics.km_splits(times, distances, split_meters=1000)

    assert len(splits) == 6
    for split in splits[:5]:
        assert split["distance_meters"] == pytest.approx(1000.0)
        assert split["duration_seconds"] == pytest.approx(300.0)
    last = splits[-1]
    assert last["distance_meters"] == pytest.approx(500.0)
    assert last["duration_seconds"] == pytest.approx(150.0)


# --- grade-adjusted pace -------------------------------------------------

def test_grade_adjusted_pace_flat_same_as_raw():
    adjusted = analytics.grade_adjusted_pace(raw_pace_sec_per_km=300, grade_percent=0)

    assert adjusted == pytest.approx(300.0)


def test_grade_adjusted_pace_uphill_slower():
    adjusted = analytics.grade_adjusted_pace(raw_pace_sec_per_km=300, grade_percent=5)

    assert adjusted > 300.0
    assert adjusted == pytest.approx(349.5, abs=0.01)


# --- TRIMP -----------------------------------------------------------------

def test_trimp_known_hr_and_duration_expected_value():
    trimp = analytics.trimp(duration_minutes=30, avg_hr=150, hr_rest=60, hr_max=190)

    assert trimp == pytest.approx(50.22, abs=0.01)


# --- CTL / ATL ---------------------------------------------------------

def test_ctl_atl_day1_value_equals_that_days_load():
    result = analytics.ctl_atl([100])

    assert result[0]["ctl"] == pytest.approx(100.0)
    assert result[0]["atl"] == pytest.approx(100.0)
    assert result[0]["form"] == pytest.approx(0.0)


def test_ctl_atl_decays_correctly_with_zero_activity_days():
    result = analytics.ctl_atl([100, 0, 50])

    assert result[1]["ctl"] == pytest.approx(97.647, abs=0.01)
    assert result[1]["atl"] == pytest.approx(86.688, abs=0.01)
    assert result[2]["ctl"] == pytest.approx(96.526, abs=0.01)
    assert result[2]["atl"] == pytest.approx(81.804, abs=0.01)
    assert result[2]["form"] == pytest.approx(result[2]["ctl"] - result[2]["atl"], abs=0.001)


# --- Riegel predictions ------------------------------------------------

def test_riegel_known_5k_time_predicts_10k_within_tolerance():
    predicted = analytics.riegel_predict(
        known_time_seconds=1500, known_distance_meters=5000, target_distance_meters=10000
    )

    assert predicted == pytest.approx(3127.4, abs=0.5)


# --- VO2max ------------------------------------------------------------

def test_vo2max_known_pace_and_hr_expected_value_within_tolerance():
    vdot = analytics.estimate_vo2max(
        distance_meters=5000, duration_seconds=1500, avg_hr=170, max_hr=190
    )

    assert vdot == pytest.approx(42.82, abs=0.01)


def test_vo2max_without_hr_returns_unadjusted_vdot():
    vdot = analytics.estimate_vo2max(distance_meters=5000, duration_seconds=1500)

    assert vdot == pytest.approx(38.31, abs=0.01)


# --- stream coalescing ---------------------------------------------------

def test_coalesce_stream_metric_drops_none_values():
    times = [0, 100, 200, 300]
    values = [None, 5.0, None, 15.0]

    ts, vs = analytics.coalesce_stream_metric(times, values)

    assert ts == [100, 300]
    assert vs == [5.0, 15.0]


# --- daily TRIMP loads / default max HR -----------------------------------

def test_build_daily_trimp_loads_fills_gaps_with_zero():
    from datetime import date

    daily_totals = {date(2026, 1, 1): 50.0, date(2026, 1, 3): 30.0}

    loads = analytics.build_daily_trimp_loads(daily_totals, date(2026, 1, 1), date(2026, 1, 3))

    assert loads == [50.0, 0.0, 30.0]


def test_default_max_hr_uses_220_minus_age_formula():
    assert analytics.default_max_hr(birth_year=1990, reference_year=2026) == 184


def test_value_at_time_returns_nearest_sample():
    times = [0, 100, 200]
    values = [10.0, 20.0, 30.0]

    assert analytics.value_at_time(times, values, 90) == 20.0
    assert analytics.value_at_time(times, values, 40) == 10.0
