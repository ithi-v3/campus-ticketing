from flask import Blueprint, jsonify

from ..models import Category, Location, PriorityLevel
from ..security import login_required

bp = Blueprint("lookups", __name__, url_prefix="/api")


@bp.get("/lookups")
@login_required
def lookups():
    return jsonify(
        categories=[
            {"category_id": c.category_id, "category_name": c.category_name,
             "description": c.description}
            for c in Category.query.order_by(Category.category_name)
        ],
        locations=[
            {"location_id": l.location_id, "block_name": l.block_name, "room": l.room,
             "location_type": l.location_type, "label": f"{l.block_name} / {l.room}"}
            for l in Location.query.order_by(Location.block_name, Location.room)
        ],
        priorities=[
            {"priority_id": p.priority_id, "priority_name": p.priority_name, "rank": p.rank,
             "escalation_days": p.escalation_days}
            for p in PriorityLevel.query.order_by(PriorityLevel.rank)
        ],
    )
