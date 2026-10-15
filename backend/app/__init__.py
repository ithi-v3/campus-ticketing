import datetime
import decimal
import os

import click
from flask import Flask, jsonify, request
from flask.json.provider import DefaultJSONProvider

from .errors import register_error_handlers
from .extensions import db


class JSONProvider(DefaultJSONProvider):
    """Dates as ISO strings and Decimals as numbers (the defaults are HTTP-date and string).
    Naive datetimes come from UTC connections, so they are tagged with Z."""

    @staticmethod
    def default(o):
        if isinstance(o, datetime.datetime):
            return o.isoformat() + ("Z" if o.tzinfo is None else "")
        if isinstance(o, datetime.date):
            return o.isoformat()
        if isinstance(o, decimal.Decimal):
            return float(o)
        return DefaultJSONProvider.default(o)


def create_app(overrides=None):
    app = Flask(__name__)
    app.json = JSONProvider(app)
    app.config.from_object("config.Config")
    if overrides:
        app.config.update(overrides)

    if not app.config.get("JWT_SECRET"):
        raise RuntimeError("JWT_SECRET is not set. Put it in backend/.env (see .env.example).")
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("DATABASE_URL is not set. Put it in backend/.env (see .env.example).")

    db.init_app(app)
    register_error_handlers(app)

    from .routes import auth, lookups, notifications, reports, tickets, users
    for module in (auth, lookups, notifications, reports, tickets, users):
        app.register_blueprint(module.bp)

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin")
        allowed = [o.strip() for o in app.config["FRONTEND_ORIGIN"].split(",")]
        if origin and origin in allowed:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
            response.headers["Vary"] = "Origin"
        return response

    register_cli(app)

    if not app.config.get("TESTING"):
        # With the debug reloader only the child process should run the sweep.
        if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
            from .escalation import start_escalation_job
            start_escalation_job(app)
    return app


def register_cli(app):
    @app.cli.command("init-db")
    @click.option("--demo", is_flag=True, help="Also load the demo users and tickets.")
    def init_db(demo):
        """Create tables, triggers and reference data from the SQL files."""
        files = ["01_schema.sql", "02_seed.sql"] + (["03_demo_data.sql"] if demo else [])
        for name in files:
            path = os.path.join(app.config["SQL_DIR"], name)
            with open(path, encoding="utf-8") as fh:
                sql = fh.read()
            conn = db.engine.raw_connection()
            try:
                cur = conn.cursor()
                cur.execute(sql)
                conn.commit()
            finally:
                conn.close()
            click.echo(f"ran {name}")
