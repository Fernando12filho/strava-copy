import tempfile
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, g, jsonify, redirect, render_template, request, url_for

from app import parser
from app.models import Activity, ActivityStream

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


@bp.route("/activities/<int:activity_id>")
def activity_detail(activity_id):
    db = get_db()
    activity = db.get(Activity, activity_id)
    if activity is None:
        return "Activity not found", 404
    return render_template("activity_detail.html", activity=activity)


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
