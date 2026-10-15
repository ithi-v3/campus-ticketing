"""Background sweep that calls escalate_overdue_tickets() every few minutes.
The trigger in Postgres does the notifying; this just makes sure something
changes the status once a ticket gets old enough."""
import threading
import time

from sqlalchemy import text

from .extensions import db


def _loop(app, minutes):
    while True:
        time.sleep(minutes * 60)
        try:
            with app.app_context():
                count = db.session.execute(text("SELECT escalate_overdue_tickets()")).scalar()
                db.session.commit()
                if count:
                    app.logger.info("auto-escalated %s ticket(s)", count)
        except Exception:
            app.logger.exception("escalation sweep failed")
            try:
                with app.app_context():
                    db.session.rollback()
            except Exception:
                pass


def start_escalation_job(app):
    minutes = app.config.get("ESCALATION_INTERVAL_MINUTES", 0)
    if minutes <= 0:
        return
    threading.Thread(target=_loop, args=(app, minutes), daemon=True, name="escalation").start()
