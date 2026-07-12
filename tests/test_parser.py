import zipfile
from datetime import datetime

import pytest

from app import parser
from app.models import Activity, ActivityStream, BestEffort

DUPLICATE_WORKOUT_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
 <Workout workoutActivityType="HKWorkoutActivityTypeRunning" duration="30.0" durationUnit="min" totalDistance="5.0" totalDistanceUnit="km" startDate="2026-07-01 08:00:00 -0700" endDate="2026-07-01 08:30:00 -0700"/>
 <Workout workoutActivityType="HKWorkoutActivityTypeRunning" duration="30.0" durationUnit="min" totalDistance="5.0" totalDistanceUnit="km" startDate="2026-07-01 08:00:00 -0700" endDate="2026-07-01 08:30:00 -0700"/>
</HealthData>"""

BILLION_LAUGHS_XML = b"""<?xml version="1.0"?>
<!DOCTYPE HealthData [
 <!ENTITY lol "lol">
 <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
]>
<HealthData>&lol2;</HealthData>"""


def test_apple_health_xml_produces_correct_activity(fixtures_dir):
    xml_bytes = (fixtures_dir / "sample_export.xml").read_bytes()

    workouts = parser.parse_apple_health_xml(xml_bytes)

    assert len(workouts) == 1
    w = workouts[0]
    assert w["activity_type"] == "Run"
    assert w["start_time"] == datetime(2026, 7, 1, 15, 0, 0)
    assert w["end_time"] == datetime(2026, 7, 1, 15, 30, 0)
    assert w["duration_seconds"] == 1800
    assert w["distance_meters"] == 5000.0


def test_two_pass_buckets_records_into_correct_workout_window(fixtures_dir):
    xml_bytes = (fixtures_dir / "sample_export.xml").read_bytes()

    workouts = parser.parse_apple_health_xml(xml_bytes)

    stream = workouts[0]["stream_data"]
    assert stream["time"] == [0, 300, 900]
    assert stream["hr"] == [None, 145.0, 152.0]
    assert stream["distance"] == [1500.0, None, None]


def test_records_outside_all_workout_windows_are_discarded_no_crash(fixtures_dir):
    xml_bytes = (fixtures_dir / "sample_export.xml").read_bytes()

    workouts = parser.parse_apple_health_xml(xml_bytes)

    stream = workouts[0]["stream_data"]
    assert len(stream["time"]) == 3
    assert all(v != 70.0 for v in stream["hr"])


def test_dedup_within_one_parse_overlapping_workouts_keeps_one():
    workouts = parser.parse_apple_health_xml(DUPLICATE_WORKOUT_XML)

    assert len(workouts) == 1


def test_dedup_across_reimports_same_zip_twice_no_duplicate_rows(fixtures_dir, db_session):
    zip_path = fixtures_dir / "sample_export.zip"

    result1 = parser.import_apple_health_zip(zip_path, db_session)
    assert result1 == {"imported": 1, "skipped": 0}

    result2 = parser.import_apple_health_zip(zip_path, db_session)
    assert result2 == {"imported": 0, "skipped": 1}

    assert db_session.query(Activity).count() == 1


def test_gpx_import_creates_activity_and_stream(fixtures_dir, db_session):
    gpx_path = fixtures_dir / "sample.gpx"

    result = parser.import_gpx(gpx_path, db_session)

    assert result == {"imported": 1, "skipped": 0}
    activity = db_session.query(Activity).one()
    assert activity.activity_type == "Run"
    assert activity.source == "gpx"
    assert activity.duration_seconds == 600
    assert activity.avg_hr == pytest.approx(147.6667, abs=0.001)
    assert activity.max_hr == 155.0
    assert activity.elevation_gain_meters == pytest.approx(5.0, abs=0.001)
    assert activity.distance_meters == pytest.approx(146.28, abs=0.5)

    stream = db_session.query(ActivityStream).filter_by(activity_id=activity.id).one()
    assert stream.stream_data["hr"] == [140.0, 148.0, 155.0]
    assert len(stream.stream_data["time"]) == 3


def test_csv_import_creates_activity_without_stream(fixtures_dir, db_session):
    csv_path = fixtures_dir / "sample.csv"

    result = parser.import_csv(csv_path, db_session)

    assert result == {"imported": 1, "skipped": 0}
    activity = db_session.query(Activity).one()
    assert activity.activity_type == "Run"
    assert activity.duration_seconds == 1800
    assert activity.distance_meters == 5000.0
    assert activity.avg_hr == 148.0
    assert activity.max_hr == 165.0
    assert activity.elevation_gain_meters == 42.0
    assert activity.source == "csv"
    assert db_session.query(ActivityStream).count() == 0


def test_zip_path_traversal_entry_raises_and_writes_nothing(tmp_path, db_session):
    evil_zip = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil_zip, "w") as zf:
        zf.writestr("../../evil.txt", "pwned")

    with pytest.raises(ValueError):
        parser.import_apple_health_zip(evil_zip, db_session)

    assert db_session.query(Activity).count() == 0
    assert not (tmp_path.parent.parent / "evil.txt").exists()


def test_zip_missing_export_xml_raises_clean_error(tmp_path, db_session):
    bad_zip = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad_zip, "w") as zf:
        zf.writestr("apple_health_export/readme.txt", "no export here")

    with pytest.raises(ValueError, match="export.xml"):
        parser.import_apple_health_zip(bad_zip, db_session)


def test_entity_expansion_attempt_is_caught():
    with pytest.raises(Exception):
        parser.parse_apple_health_xml(BILLION_LAUGHS_XML)


def test_update_best_efforts_creates_pr_row(db_session, make_activity):
    activity = make_activity(distance_meters=10000.0, duration_seconds=3000, dedup_key="be-1")
    times = [i * 300 for i in range(11)]
    distances = [i * 1000.0 for i in range(11)]
    stream_data = {"time": times, "hr": [None] * 11, "distance": distances, "elevation": [], "pace": []}

    parser.update_best_efforts(db_session, activity, stream_data)

    five_k = db_session.query(BestEffort).filter_by(distance_label="5K").one()
    assert five_k.duration_seconds == pytest.approx(1500.0, abs=0.01)
    assert five_k.activity_id == activity.id


def test_update_best_efforts_pr_replaces_old(db_session, make_activity):
    slow_activity = make_activity(dedup_key="slow")
    fast_activity = make_activity(dedup_key="fast")
    slow_stream = {"time": [0, 1800], "hr": [None, None], "distance": [0, 5000.0], "elevation": [], "pace": []}
    fast_stream = {"time": [0, 1400], "hr": [None, None], "distance": [0, 5000.0], "elevation": [], "pace": []}

    parser.update_best_efforts(db_session, slow_activity, slow_stream)
    parser.update_best_efforts(db_session, fast_activity, fast_stream)

    five_k = db_session.query(BestEffort).filter_by(distance_label="5K").one()
    assert five_k.activity_id == fast_activity.id
    assert five_k.duration_seconds == pytest.approx(1400.0, abs=0.01)


def test_update_best_efforts_non_pr_does_not_overwrite(db_session, make_activity):
    fast_activity = make_activity(dedup_key="fast")
    slow_activity = make_activity(dedup_key="slow")
    fast_stream = {"time": [0, 1400], "hr": [None, None], "distance": [0, 5000.0], "elevation": [], "pace": []}
    slow_stream = {"time": [0, 1800], "hr": [None, None], "distance": [0, 5000.0], "elevation": [], "pace": []}

    parser.update_best_efforts(db_session, fast_activity, fast_stream)
    parser.update_best_efforts(db_session, slow_activity, slow_stream)

    five_k = db_session.query(BestEffort).filter_by(distance_label="5K").one()
    assert five_k.activity_id == fast_activity.id
    assert five_k.duration_seconds == pytest.approx(1400.0, abs=0.01)
