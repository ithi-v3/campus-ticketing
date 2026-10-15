import os

from dotenv import load_dotenv

load_dotenv()


def _db_url():
    url = os.environ.get("DATABASE_URL", "")
    # Render and Heroku hand out postgres:// URLs, SQLAlchemy wants postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    SQLALCHEMY_DATABASE_URI = _db_url()
    # Timestamps are stored as naive columns, so pin every connection to UTC and
    # let the browser convert to the viewer's local time.
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True,
                                 "connect_args": {"options": "-c timezone=UTC"}}
    JWT_SECRET = os.environ.get("JWT_SECRET")
    JWT_HOURS = 8
    FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
    ESCALATION_INTERVAL_MINUTES = int(os.environ.get("ESCALATION_INTERVAL_MINUTES", "10"))
    SQL_DIR = os.environ.get(
        "SQL_DIR", os.path.join(os.path.dirname(__file__), "..", "database")
    )
