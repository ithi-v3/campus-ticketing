from flask import Blueprint, g, jsonify
from sqlalchemy import text

from ..errors import ApiError
from ..extensions import db
from ..security import roles_required

bp = Blueprint("reports", __name__, url_prefix="/api/reports")

REPORT_COLUMNS = ("technician_id", "technician_name", "tickets_assigned", "tickets_resolved",
                  "open_load", "avg_resolution_hours", "avg_rating")


def technician_report(technician_id=None):
    rows = db.session.execute(text("SELECT * FROM sp_resolution_report(:tid)"),
                              {"tid": technician_id}).mappings().all()
    return [dict(r) for r in rows]


@bp.get("/summary")
@roles_required("Admin")
def summary():
    by_status = db.session.execute(text("""
        SELECT s.status, COUNT(t.ticket_id) AS count
        FROM (VALUES ('Open'), ('Assigned'), ('Escalated'), ('Resolved'), ('Closed')) AS s(status)
        LEFT JOIN tickets t ON t.status = s.status
        GROUP BY s.status
        ORDER BY array_position(ARRAY['Open','Assigned','Escalated','Resolved','Closed'], s.status)
        """)).mappings().all()

    by_category = db.session.execute(text("""
        SELECT c.category_name, COUNT(t.ticket_id) AS count
        FROM categories c LEFT JOIN tickets t ON t.category_id = c.category_id
        GROUP BY c.category_name ORDER BY count DESC, c.category_name
        """)).mappings().all()

    overall = db.session.execute(text("""
        SELECT COUNT(*) AS total,
               COUNT(*) FILTER (WHERE status IN ('Open', 'Escalated')) AS awaiting_assignment,
               ROUND(AVG(EXTRACT(EPOCH FROM (resolved_at - created_at)) / 3600.0)
                     FILTER (WHERE resolved_at IS NOT NULL), 1) AS avg_resolution_hours,
               (SELECT ROUND(AVG(rating), 2) FROM feedback) AS avg_rating
        FROM tickets""")).mappings().one()

    return jsonify(overall=dict(overall), by_status=[dict(r) for r in by_status],
                   by_category=[dict(r) for r in by_category])


@bp.get("/technicians")
@roles_required("Admin")
def all_technicians():
    return jsonify(items=technician_report())


@bp.get("/technicians/<int:technician_id>")
@roles_required("Admin")
def one_technician(technician_id):
    rows = technician_report(technician_id)
    if not rows:
        raise ApiError("Technician not found.", 404)
    return jsonify(report=rows[0])


@bp.get("/me")
@roles_required("Technician")
def my_report():
    rows = technician_report(g.user.user_id)
    return jsonify(report=rows[0] if rows else None)


@bp.post("/escalate")
@roles_required("Admin")
def run_escalation():
    """Run the overdue sweep now instead of waiting for the background job."""
    count = db.session.execute(text("SELECT escalate_overdue_tickets()")).scalar()
    db.session.commit()
    return jsonify(escalated=count)
