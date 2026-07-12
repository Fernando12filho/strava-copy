import io

import pytest


def test_index_redirects_to_activities(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/activities")


def test_activity_list_returns_200(client, make_activity):
    make_activity()
    response = client.get("/activities")
    assert response.status_code == 200


def test_activity_list_filtered_by_type(client, make_activity):
    run = make_activity(activity_type="Run", dedup_key="run-key")
    walk = make_activity(activity_type="Walk", dedup_key="walk-key")

    response = client.get("/activities?type=Run")

    body = response.data.decode()
    assert f'data-activity-id="{run.id}"' in body
    assert f'data-activity-id="{walk.id}"' not in body


def test_activity_list_filtered_by_date_range(client, make_activity):
    from datetime import datetime

    early = make_activity(
        start_time=datetime(2026, 1, 1, 8, 0, 0),
        end_time=datetime(2026, 1, 1, 8, 30, 0),
        dedup_key="early-key",
    )
    late = make_activity(
        start_time=datetime(2026, 6, 1, 8, 0, 0),
        end_time=datetime(2026, 6, 1, 8, 30, 0),
        dedup_key="late-key",
    )

    response = client.get("/activities?from=2026-05-01&to=2026-07-01")

    body = response.data.decode()
    assert f'data-activity-id="{late.id}"' in body
    assert f'data-activity-id="{early.id}"' not in body


def test_activity_detail_returns_200_for_existing(client, make_activity):
    activity = make_activity()
    response = client.get(f"/activities/{activity.id}")
    assert response.status_code == 200


def test_activity_detail_computes_splits_from_stream(client, make_activity, db_session):
    from app.models import ActivityStream

    activity = make_activity(duration_seconds=1500, distance_meters=5000.0)
    times = [i * 300 for i in range(6)]
    distances = [i * 1000.0 for i in range(6)]
    db_session.add(
        ActivityStream(
            activity_id=activity.id,
            stream_data={"time": times, "hr": [None] * 6, "distance": distances, "elevation": [], "pace": []},
        )
    )
    db_session.commit()

    response = client.get(f"/activities/{activity.id}")

    assert response.status_code == 200
    body = response.data.decode()
    assert body.count("data-split-index") == 5


def test_activity_detail_returns_404_for_missing(client):
    response = client.get("/activities/999")
    assert response.status_code == 404


def test_activity_stream_json_has_expected_keys(client, make_activity, db_session):
    from app.models import ActivityStream

    activity = make_activity()
    db_session.add(
        ActivityStream(
            activity_id=activity.id,
            stream_data={"hr": [140], "pace": [], "elevation": [], "distance": [0], "time": [0]},
        )
    )
    db_session.commit()

    response = client.get(f"/activities/{activity.id}/stream.json")

    assert response.status_code == 200
    data = response.get_json()
    assert set(data.keys()) == {"hr", "pace", "elevation", "distance", "time"}


def test_import_valid_zip_returns_200_and_summary(client, fixtures_dir):
    zip_bytes = (fixtures_dir / "sample_export.zip").read_bytes()

    response = client.post(
        "/import",
        data={"file": (io.BytesIO(zip_bytes), "sample_export.zip")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data == {"imported": 1, "skipped": 0}


def test_import_invalid_file_type_returns_400(client):
    response = client.post(
        "/import",
        data={"file": (io.BytesIO(b"not a valid import"), "notes.txt")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400


def test_import_oversized_returns_413(app):
    app.config["MAX_UPLOAD_BYTES"] = 10
    test_client = app.test_client()

    response = test_client.post(
        "/import",
        data={"file": (io.BytesIO(b"x" * 1000), "big.gpx")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 413


def test_import_page_returns_200(client):
    response = client.get("/import")
    assert response.status_code == 200


def test_settings_page_get_returns_200(client):
    response = client.get("/settings")
    assert response.status_code == 200


def test_settings_page_post_creates_settings(client, db_session):
    from app.models import UserSettings

    response = client.post(
        "/settings", data={"resting_hr": "55", "max_hr": "185", "birth_year": "1990"}
    )

    assert response.status_code == 302
    stored = db_session.query(UserSettings).one()
    assert stored.resting_hr == 55
    assert stored.max_hr == 185
    assert stored.birth_year == 1990


def test_settings_page_post_updates_existing_row(client, db_session):
    from app.models import UserSettings

    client.post("/settings", data={"resting_hr": "55", "max_hr": "185", "birth_year": "1990"})
    client.post("/settings", data={"resting_hr": "60", "max_hr": "190", "birth_year": "1991"})

    assert db_session.query(UserSettings).count() == 1
    stored = db_session.query(UserSettings).one()
    assert stored.resting_hr == 60


def test_dashboard_returns_200(client, make_activity):
    make_activity()
    response = client.get("/dashboard")
    assert response.status_code == 200


def test_dashboard_returns_200_with_no_activities(client):
    response = client.get("/dashboard")
    assert response.status_code == 200
