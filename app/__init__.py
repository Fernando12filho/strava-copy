import os
from pathlib import Path

from flask import Flask, g
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app import analytics
from app.models import Base

# Base.metadata.create_all() only creates tables that don't exist yet — it never
# alters an existing table. data/fitness.db predates these columns, so on an
# existing table we add whatever's missing by hand instead of wiping the file.
_SCHEMA_UPGRADES = {
    "activities": ["title", "source_device"],
    "user_settings": ["weight_kg", "units"],
}


def _apply_schema_upgrades(engine):
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table_name, required_columns in _SCHEMA_UPGRADES.items():
            if table_name not in existing_tables:
                continue
            existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
            for column_name in required_columns:
                if column_name in existing_columns:
                    continue
                column = Base.metadata.tables[table_name].columns[column_name]
                column_type = column.type.compile(engine.dialect)
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))


def create_app(config=None):
    app = Flask(__name__)
    app.config.setdefault(
        "DATABASE_URL", os.environ.get("DISTRAVA_DATABASE_URL", "sqlite:///./data/fitness.db")
    )
    if config:
        app.config.update(config)

    engine = app.config.get("ENGINE")
    if engine is None:
        database_url = app.config["DATABASE_URL"]
        if database_url.startswith("sqlite:///./"):
            db_path = Path(database_url.replace("sqlite:///./", "", 1))
            db_path.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(database_url, connect_args={"check_same_thread": False})

    Base.metadata.create_all(engine)
    _apply_schema_upgrades(engine)
    app.engine = engine
    app.session_factory = sessionmaker(bind=engine)

    app.jinja_env.filters["format_duration"] = analytics.format_duration
    app.jinja_env.filters["format_pace"] = analytics.format_pace

    from app.routes import bp

    app.register_blueprint(bp)

    @app.teardown_appcontext
    def close_session(exception=None):
        session = g.pop("db_session", None)
        if session is not None:
            session.close()

    return app
