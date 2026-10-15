from flask import Blueprint, g, jsonify

from ..errors import ApiError
from ..extensions import db
from ..models import Notification
from ..security import login_required

bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


def _row(n):
    return {"notification_id": n.notification_id, "ticket_id": n.ticket_id,
            "message": n.message, "is_read": n.is_read, "created_at": n.created_at}


@bp.get("")
@login_required
def list_notifications():
    rows = (Notification.query.filter_by(user_id=g.user.user_id)
            .order_by(Notification.created_at.desc(), Notification.notification_id.desc())
            .limit(50).all())
    unread = Notification.query.filter_by(user_id=g.user.user_id, is_read=False).count()
    return jsonify(items=[_row(n) for n in rows], unread=unread)


@bp.post("/<int:notification_id>/read")
@login_required
def mark_read(notification_id):
    n = db.session.get(Notification, notification_id)
    if n is None or n.user_id != g.user.user_id:
        raise ApiError("Notification not found.", 404)
    n.is_read = True
    db.session.commit()
    return jsonify(ok=True)


@bp.post("/read-all")
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=g.user.user_id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify(ok=True)
