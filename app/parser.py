import csv
import hashlib
import io
import zipfile
from datetime import datetime, timedelta, timezone
from math import atan2, cos, radians, sin, sqrt

import defusedxml.ElementTree as ET

from app.models import Activity, ActivityStream

APPLE_DATE_FMT = "%Y-%m-%d %H:%M:%S %z"
EARTH_RADIUS_M = 6371000

ACTIVITY_TYPE_MAP = {"running": "Run", "walking": "Walk", "cycling": "Cycle"}

RECORD_TYPES = {
    "HKQuantityTypeIdentifierHeartRate": "hr",
    "HKQuantityTypeIdentifierDistanceWalkingRunning": "distance",
}

GPX_NS = {
    "gpx": "http://www.topografix.com/GPX/1/1",
    "gpxtpx": "http://www.garmin.com/xmlschemas/TrackPointExtension/v1",
}


def _normalize_activity_type(raw):
    if raw.startswith("HKWorkoutActivityType"):
        raw = raw[len("HKWorkoutActivityType"):]
    return ACTIVITY_TYPE_MAP.get(raw.lower(), raw)


def _to_meters(value, unit):
    value = float(value)
    if unit == "km":
        return value * 1000
    if unit == "mi":
        return value * 1609.344
    return value


def _to_seconds(value, unit):
    value = float(value)
    if unit == "min":
        return int(round(value * 60))
    if unit == "hr":
        return int(round(value * 3600))
    return int(round(value))


def _parse_apple_date(raw):
    return datetime.strptime(raw, APPLE_DATE_FMT).astimezone(timezone.utc).replace(tzinfo=None)


def _drop_overlapping_duplicates(windows):
    kept = []
    for w in windows:
        overlaps = any(
            w["activity_type"] == k["activity_type"]
            and w["start_time"] < k["end_time"]
            and k["start_time"] < w["end_time"]
            for k in kept
        )
        if not overlaps:
            kept.append(w)
    return kept


def _collect_workout_windows(xml_bytes):
    windows = []
    for _, elem in ET.iterparse(io.BytesIO(xml_bytes), events=("end",)):
        if elem.tag == "Workout":
            total_distance = elem.get("totalDistance")
            windows.append(
                {
                    "activity_type": _normalize_activity_type(elem.get("workoutActivityType")),
                    "start_time": _parse_apple_date(elem.get("startDate")),
                    "end_time": _parse_apple_date(elem.get("endDate")),
                    "duration_seconds": _to_seconds(elem.get("duration"), elem.get("durationUnit")),
                    "distance_meters": (
                        _to_meters(total_distance, elem.get("totalDistanceUnit"))
                        if total_distance is not None
                        else 0.0
                    ),
                }
            )
        elem.clear()
    return _drop_overlapping_duplicates(windows)


def _bucket_records(xml_bytes, windows):
    buckets = [{} for _ in windows]
    for _, elem in ET.iterparse(io.BytesIO(xml_bytes), events=("end",)):
        if elem.tag == "Record":
            metric = RECORD_TYPES.get(elem.get("type"))
            if metric is not None:
                start = _parse_apple_date(elem.get("startDate"))
                value = float(elem.get("value"))
                if metric == "distance":
                    value = _to_meters(value, elem.get("unit"))
                for i, w in enumerate(windows):
                    if w["start_time"] <= start <= w["end_time"]:
                        elapsed = int((start - w["start_time"]).total_seconds())
                        buckets[i].setdefault(elapsed, {})[metric] = value
                        break
        elem.clear()

    streams = []
    for bucket in buckets:
        times = sorted(bucket.keys())
        streams.append(
            {
                "time": times,
                "hr": [bucket[t].get("hr") for t in times],
                "distance": [bucket[t].get("distance") for t in times],
                "elevation": [],
                "pace": [],
            }
        )
    return streams


def parse_apple_health_xml(xml_bytes):
    windows = _collect_workout_windows(xml_bytes)
    streams = _bucket_records(xml_bytes, windows)
    for w, stream in zip(windows, streams):
        w["stream_data"] = stream
    return windows


def _make_dedup_key(activity_type, start_time, duration_seconds):
    raw = f"{activity_type}|{start_time.isoformat()}|{duration_seconds}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _persist_activity(
    db_session,
    activity_type,
    start_time,
    end_time,
    duration_seconds,
    distance_meters,
    avg_hr,
    max_hr,
    elevation_gain_meters,
    source,
    source_id,
    stream_data=None,
):
    dedup_key = _make_dedup_key(activity_type, start_time, duration_seconds)
    existing = db_session.query(Activity).filter_by(dedup_key=dedup_key).first()
    if existing:
        return False

    activity = Activity(
        activity_type=activity_type,
        start_time=start_time,
        end_time=end_time,
        duration_seconds=duration_seconds,
        distance_meters=distance_meters,
        avg_hr=avg_hr,
        max_hr=max_hr,
        elevation_gain_meters=elevation_gain_meters,
        source=source,
        source_id=source_id,
        dedup_key=dedup_key,
    )
    db_session.add(activity)
    db_session.flush()
    if stream_data is not None:
        db_session.add(ActivityStream(activity_id=activity.id, stream_data=stream_data))
    db_session.commit()
    return True


def _is_unsafe_zip_entry(name):
    if name.startswith("/") or name.startswith("\\"):
        return True
    parts = name.replace("\\", "/").split("/")
    return ".." in parts


def _read_export_xml(zip_path):
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        for name in names:
            if _is_unsafe_zip_entry(name):
                raise ValueError(f"unsafe zip entry: {name}")
        export_name = next((n for n in names if n.endswith("export.xml")), None)
        if export_name is None:
            raise ValueError("export.xml not found in zip")
        return zf.read(export_name)


def import_apple_health_zip(zip_path, db_session):
    xml_bytes = _read_export_xml(zip_path)
    workouts = parse_apple_health_xml(xml_bytes)

    imported = 0
    skipped = 0
    for w in workouts:
        hr_values = [v for v in w["stream_data"]["hr"] if v is not None]
        created = _persist_activity(
            db_session,
            activity_type=w["activity_type"],
            start_time=w["start_time"],
            end_time=w["end_time"],
            duration_seconds=w["duration_seconds"],
            distance_meters=w["distance_meters"],
            avg_hr=(sum(hr_values) / len(hr_values)) if hr_values else None,
            max_hr=max(hr_values) if hr_values else None,
            elevation_gain_meters=None,
            source="apple_health",
            source_id=None,
            stream_data=w["stream_data"],
        )
        if created:
            imported += 1
        else:
            skipped += 1
    return {"imported": imported, "skipped": skipped}


def _haversine(lat1, lon1, lat2, lon2):
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * atan2(sqrt(a), sqrt(1 - a))


def _parse_gpx_time(raw):
    return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ")


def import_gpx(file_path, db_session):
    tree = ET.parse(str(file_path))
    root = tree.getroot()
    trkpts = root.findall(".//gpx:trkpt", GPX_NS)
    if not trkpts:
        raise ValueError("no track points found in gpx file")

    points = []
    for pt in trkpts:
        ele_el = pt.find("gpx:ele", GPX_NS)
        time_el = pt.find("gpx:time", GPX_NS)
        hr_el = pt.find("gpx:extensions/gpxtpx:TrackPointExtension/gpxtpx:hr", GPX_NS)
        points.append(
            {
                "lat": float(pt.get("lat")),
                "lon": float(pt.get("lon")),
                "ele": float(ele_el.text) if ele_el is not None else None,
                "time": _parse_gpx_time(time_el.text),
                "hr": float(hr_el.text) if hr_el is not None else None,
            }
        )

    start_time = points[0]["time"]
    end_time = points[-1]["time"]
    duration_seconds = int((end_time - start_time).total_seconds())

    distance_meters = 0.0
    elevation_gain = 0.0
    cumulative_distances = [0.0]
    for prev, curr in zip(points, points[1:]):
        leg = _haversine(prev["lat"], prev["lon"], curr["lat"], curr["lon"])
        distance_meters += leg
        cumulative_distances.append(distance_meters)
        if prev["ele"] is not None and curr["ele"] is not None and curr["ele"] > prev["ele"]:
            elevation_gain += curr["ele"] - prev["ele"]

    hr_values = [p["hr"] for p in points if p["hr"] is not None]
    avg_hr = sum(hr_values) / len(hr_values) if hr_values else None
    max_hr = max(hr_values) if hr_values else None

    activity_type_raw = root.findtext(".//gpx:type", default="Run", namespaces=GPX_NS)
    activity_type = _normalize_activity_type(activity_type_raw)

    stream_data = {
        "time": [int((p["time"] - start_time).total_seconds()) for p in points],
        "hr": [p["hr"] for p in points],
        "distance": cumulative_distances,
        "elevation": [p["ele"] for p in points],
        "pace": [],
    }

    created = _persist_activity(
        db_session,
        activity_type=activity_type,
        start_time=start_time,
        end_time=end_time,
        duration_seconds=duration_seconds,
        distance_meters=distance_meters,
        avg_hr=avg_hr,
        max_hr=max_hr,
        elevation_gain_meters=elevation_gain,
        source="gpx",
        source_id=None,
        stream_data=stream_data,
    )
    return {"imported": 1, "skipped": 0} if created else {"imported": 0, "skipped": 1}


def import_csv(file_path, db_session):
    imported = 0
    skipped = 0
    with open(file_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            start_time = datetime.fromisoformat(row["date"])
            duration_seconds = int(row["duration_seconds"])
            end_time = start_time + timedelta(seconds=duration_seconds)
            created = _persist_activity(
                db_session,
                activity_type=_normalize_activity_type(row["activity_type"]),
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration_seconds,
                distance_meters=float(row["distance_meters"]),
                avg_hr=float(row["avg_hr"]) if row.get("avg_hr") else None,
                max_hr=float(row["max_hr"]) if row.get("max_hr") else None,
                elevation_gain_meters=(
                    float(row["elevation_gain_meters"]) if row.get("elevation_gain_meters") else None
                ),
                source="csv",
                source_id=None,
                stream_data=None,
            )
            if created:
                imported += 1
            else:
                skipped += 1
    return {"imported": imported, "skipped": skipped}
