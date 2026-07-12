import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import Blueprint, current_app, g, jsonify, redirect, render_template, request, url_for

from app import analytics, parser
from app.models import Activity, ActivityStream, BestEffort, UserSettings

bp = Blueprint("main", __name__)

MAX_UPLOAD_BYTES = 200 * 1024 * 1024
ALLOWED_IMPORT_EXTENSIONS = {".zip", ".gpx", ".csv"}


def get_db():
    if "db_session" not in g:
        g.db_session = current_app.session_factory()
    return g.db_session


@bp.route("/")
def index():
    return redirect(url_for("main.activity_list"))


@bp.route("/activities")
def activity_list():
    db = get_db()
    query = db.query(Activity)

    activity_type = request.args.get("type")
    if activity_type:
        query = query.filter(Activity.activity_type == activity_type)

    date_from = request.args.get("from")
    if date_from:
        query = query.filter(Activity.start_time >= datetime.fromisoformat(date_from))

    date_to = request.args.get("to")
    if date_to:
        query = query.filter(Activity.start_time <= datetime.fromisoformat(date_to))

    activities = query.order_by(Activity.start_time.desc()).all()
    return render_template("activity_list.html", activities=activities)


def _compute_splits(stream_data):
    times, distances = analytics.coalesce_stream_metric(stream_data["time"], stream_data["distance"])
    if len(times) < 2:
        return []

    splits = analytics.km_splits(times, distances)

    elev_times, elevations = analytics.coalesce_stream_metric(
        stream_data["time"], stream_data.get("elevation", [])
    )
    cumulative_time = times[0]
    prev_elevation = analytics.value_at_time(elev_times, elevations, cumulative_time) if elev_times else None
    for split in splits:
        cumulative_time += split["duration_seconds"]
        curr_elevation = analytics.value_at_time(elev_times, elevations, cumulative_time) if elev_times else None
        if prev_elevation is not None and curr_elevation is not None and split["distance_meters"] > 0:
            grade_percent = (curr_elevation - prev_elevation) / split["distance_meters"] * 100
            split["grade_adjusted_pace_seconds"] = analytics.grade_adjusted_pace(
                split["pace_per_km_seconds"], grade_percent
            )
        else:
            split["grade_adjusted_pace_seconds"] = None
        prev_elevation = curr_elevation
    return splits


@bp.route("/activities/<int:activity_id>")
def activity_detail(activity_id):
    db = get_db()
    activity = db.get(Activity, activity_id)
    if activity is None:
        return "Activity not found", 404

    stream = db.query(ActivityStream).filter_by(activity_id=activity_id).first()
    splits = _compute_splits(stream.stream_data) if stream is not None else []

    return render_template("activity_detail.html", activity=activity, splits=splits)


@bp.route("/activities/<int:activity_id>/stream.json")
def activity_stream(activity_id):
    db = get_db()
    activity = db.get(Activity, activity_id)
    if activity is None:
        return jsonify({"error": "not found"}), 404

    stream = db.query(ActivityStream).filter_by(activity_id=activity_id).first()
    if stream is None:
        return jsonify({"hr": [], "pace": [], "elevation": [], "distance": [], "time": []})
    return jsonify(stream.stream_data)


@bp.route("/import", methods=["GET"])
def import_page():
    return render_template("import.html")


@bp.route("/import", methods=["POST"])
def import_file():
    if "file" not in request.files:
        return jsonify({"error": "no file provided"}), 400

    upload = request.files["file"]
    filename = upload.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_IMPORT_EXTENSIONS:
        return jsonify({"error": f"unsupported file type: {suffix}"}), 400

    upload.seek(0, 2)
    size = upload.tell()
    upload.seek(0)
    max_upload_bytes = current_app.config.get("MAX_UPLOAD_BYTES", MAX_UPLOAD_BYTES)
    if size > max_upload_bytes:
        return jsonify({"error": "file too large"}), 413

    db = get_db()
    tmp_path = Path(tempfile.gettempdir()) / filename
    upload.save(tmp_path)
    try:
        if suffix == ".zip":
            result = parser.import_apple_health_zip(tmp_path, db)
        elif suffix == ".gpx":
            result = parser.import_gpx(tmp_path, db)
        else:
            result = parser.import_csv(tmp_path, db)
    finally:
        tmp_path.unlink(missing_ok=True)

    return jsonify(result), 200


DEFAULT_RESTING_HR = 60
DEFAULT_MAX_HR = 190
MONTHLY_TREND_MONTHS = 6


@bp.route("/settings", methods=["GET", "POST"])
def settings_page():
    db = get_db()
    settings = db.query(UserSettings).first()

    if request.method == "POST":
        if settings is None:
            settings = UserSettings()
            db.add(settings)
        resting_hr = request.form.get("resting_hr")
        max_hr = request.form.get("max_hr")
        birth_year = request.form.get("birth_year")
        settings.resting_hr = int(resting_hr) if resting_hr else None
        settings.max_hr = int(max_hr) if max_hr else None
        settings.birth_year = int(birth_year) if birth_year else None
        db.commit()
        return redirect(url_for("main.settings_page"))

    return render_template("settings.html", settings=settings)


def _resolve_hr_profile(settings, today):
    resting_hr = settings.resting_hr if settings and settings.resting_hr else DEFAULT_RESTING_HR
    if settings and settings.max_hr:
        max_hr = settings.max_hr
    elif settings and settings.birth_year:
        max_hr = analytics.default_max_hr(settings.birth_year, today.year)
    else:
        max_hr = DEFAULT_MAX_HR
    return resting_hr, max_hr


@bp.route("/dashboard")
def dashboard():
    db = get_db()
    today = date.today()
    week_ago = today - timedelta(days=7)
    trend_start = (today.replace(day=1) - timedelta(days=30 * (MONTHLY_TREND_MONTHS - 1))).replace(day=1)

    activities = db.query(Activity).order_by(Activity.start_time.asc()).all()

    week_activities = [a for a in activities if a.start_time.date() >= week_ago]
    weekly_distance = sum(a.distance_meters for a in week_activities)
    weekly_duration = sum(a.duration_seconds for a in week_activities)

    monthly_totals = {}
    for a in activities:
        if a.start_time.date() < trend_start:
            continue
        key = a.start_time.strftime("%Y-%m")
        monthly_totals[key] = monthly_totals.get(key, 0.0) + a.distance_meters
    monthly_trend = sorted(monthly_totals.items())

    settings = db.query(UserSettings).first()
    resting_hr, max_hr = _resolve_hr_profile(settings, today)

    daily_totals = {}
    for a in activities:
        if a.avg_hr is None:
            continue
        day = a.start_time.date()
        load = analytics.trimp(a.duration_seconds / 60, a.avg_hr, resting_hr, max_hr)
        daily_totals[day] = daily_totals.get(day, 0.0) + load

    if daily_totals:
        start_date = min(daily_totals.keys())
        loads = analytics.build_daily_trimp_loads(daily_totals, start_date, today)
        current_fitness = analytics.ctl_atl(loads)[-1]
    else:
        current_fitness = {"ctl": 0.0, "atl": 0.0, "form": 0.0}

    best_efforts = db.query(BestEffort).order_by(BestEffort.distance_meters.asc()).all()

    return render_template(
        "dashboard.html",
        weekly_distance=weekly_distance,
        weekly_duration=weekly_duration,
        monthly_trend=monthly_trend,
        current_fitness=current_fitness,
        best_efforts=best_efforts,
    )
