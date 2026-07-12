from pathlib import Path

from flask import Flask, g
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base


def create_app(config=None):
    app = Flask(__name__)
    app.config.setdefault("DATABASE_URL", "sqlite:///./data/fitness.db")
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
    app.engine = engine
    app.session_factory = sessionmaker(bind=engine)

    from app.routes import bp

    app.register_blueprint(bp)

    @app.teardown_appcontext
    def close_session(exception=None):
        session = g.pop("db_session", None)
        if session is not None:
            session.close()

    return app
