from flask import Blueprint, g, jsonify, request
from sqlalchemy import text

from ..errors import ApiError
from ..extensions import db
from ..models import (Category, Feedback, Location, Notification, PriorityLevel, Role, Ticket,
                      TicketAssignment, User)
from ..security import login_required, roles_required
from ..utils import get_int, get_json, get_str, page_args

bp = Blueprint("tickets", __name__, url_prefix="/api")

STATUSES = ("Open", "Assigned", "Escalated", "Resolved", "Closed")
SORTS = {
    "created_at": "created_at",
    "updated_at": "updated_at",
    "priority": "priority_rank",
    "status": "status",
}


# ---------------------------------------------------------------- helpers

def set_actor():
    """Tell the status-history trigger who is making this change.
    set_config(..., true) is the same as SET LOCAL: it lasts for this transaction only."""
    db.session.execute(text("SELECT set_config('app.user_id', :uid, true)"),
                       {"uid": str(g.user.user_id)})


def notify(user_id, ticket, message):
    if user_id and user_id != g.user.user_id:
        db.session.add(Notification(user_id=user_id, ticket_id=ticket.ticket_id, message=message))


def summary(ticket_id):
    row = db.session.execute(text("SELECT * FROM vw_ticket_summary WHERE ticket_id = :id"),
                             {"id": ticket_id}).mappings().first()
    return dict(row) if row else None


def current_technician_id(ticket_id):
    a = TicketAssignment.query.filter_by(ticket_id=ticket_id, is_current=True).first()
    return a.technician_id if a else None


def load_ticket(ticket_id):
    ticket = db.session.get(Ticket, ticket_id)
    if ticket is None:
        raise ApiError("Ticket not found.", 404)
    return ticket


def check_can_view(ticket):
    user = g.user
    if user.role_name == "Admin" or ticket.user_id == user.user_id:
        return
    if user.role_name == "Technician" and current_technician_id(ticket.ticket_id) == user.user_id:
        return
    # 404 rather than 403 so ticket ids can't be probed
    raise ApiError("Ticket not found.", 404)


def like_pattern(term):
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def list_tickets(scope):
    """scope is 'all', 'mine' (raised by me) or 'assigned' (assigned to me)."""
    where, params = [], {}

    if scope == "mine":
        where.append("reporter_id = :me")
        params["me"] = g.user.user_id
    elif scope == "assigned":
        where.append("technician_id = :me")
        params["me"] = g.user.user_id

    status = request.args.get("status")
    if status:
        if status not in STATUSES:
            raise ApiError("Unknown status filter.")
        where.append("status = :status")
        params["status"] = status

    for arg, col in (("category_id", "category_id"), ("priority_id", "priority_id"),
                     ("location_id", "location_id")):
        raw = request.args.get(arg)
        if raw:
            try:
                params[arg] = int(raw)
            except ValueError:
                raise ApiError(f"{arg} must be a number.")
            where.append(f"{col} = :{arg}")

    q = (request.args.get("q") or "").strip()
    if q:
        params["q"] = like_pattern(q)
        clause = ("(title ILIKE :q ESCAPE '\\' OR description ILIKE :q ESCAPE '\\' "
                  "OR reporter_name ILIKE :q ESCAPE '\\' OR location_label ILIKE :q ESCAPE '\\'")
        if q.isdigit():
            params["qid"] = int(q)
            clause += " OR ticket_id = :qid"
        where.append(clause + ")")

    sort_col = SORTS.get(request.args.get("sort", "created_at"))
    if sort_col is None:
        raise ApiError("Unknown sort option.")
    direction = "ASC" if request.args.get("dir") == "asc" else "DESC"

    page, per_page = page_args()
    params["limit"], params["offset"] = per_page, (page - 1) * per_page

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    total = db.session.execute(
        text(f"SELECT COUNT(*) FROM vw_ticket_summary {where_sql}"), params).scalar()
    rows = db.session.execute(
        text(f"SELECT * FROM vw_ticket_summary {where_sql} "
             f"ORDER BY {sort_col} {direction}, ticket_id DESC LIMIT :limit OFFSET :offset"),
        params).mappings().all()

    return jsonify(items=[dict(r) for r in rows], total=total, page=page, per_page=per_page,
                   pages=max((total + per_page - 1) // per_page, 1))


# ---------------------------------------------------------------- list / create

@bp.get("/tickets")
@roles_required("Admin")
def all_tickets():
    return list_tickets("all")


@bp.get("/tickets/mine")
@login_required
def my_tickets():
    return list_tickets("mine")


@bp.get("/tickets/assigned")
@roles_required("Technician", "Admin")
def assigned_tickets():
    return list_tickets("assigned")


@bp.post("/tickets")
@roles_required("Student")
def create_ticket():
    data = get_json()
    title = get_str(data, "title", 150)
    description = get_str(data, "description", 2000)
    category = db.session.get(Category, get_int(data, "category_id"))
    location = db.session.get(Location, get_int(data, "location_id"))
    if category is None:
        raise ApiError("Pick a valid category.")
    if location is None:
        raise ApiError("Pick a valid location.")

    priority_id = get_int(data, "priority_id", required=False)
    if priority_id is None:
        priority = PriorityLevel.query.filter_by(priority_name="Medium").one()
    else:
        priority = db.session.get(PriorityLevel, priority_id)
        if priority is None:
            raise ApiError("Pick a valid priority.")
    # Critical is for admins/the escalation job; students can ask for up to High.
    if priority.priority_name == "Critical":
        raise ApiError("Students can choose Low, Medium or High priority.")

    set_actor()
    ticket = Ticket(title=title, description=description, user_id=g.user.user_id,
                    category_id=category.category_id, location_id=location.location_id,
                    priority_id=priority.priority_id)
    db.session.add(ticket)
    db.session.flush()

    admins = (User.query.join(Role, Role.role_id == User.role_id)
              .filter(Role.role_name == "Admin", User.is_active.is_(True)))
    for admin in admins:
        db.session.add(Notification(user_id=admin.user_id, ticket_id=ticket.ticket_id,
                                    message=f"New ticket #{ticket.ticket_id}: {title[:80]}"))
    db.session.commit()
    return jsonify(ticket=summary(ticket.ticket_id)), 201


# ---------------------------------------------------------------- detail

@bp.get("/tickets/<int:ticket_id>")
@login_required
def ticket_detail(ticket_id):
    ticket = load_ticket(ticket_id)
    check_can_view(ticket)

    history = db.session.execute(text("""
        SELECT h.history_id, h.old_status, h.new_status, h.changed_at, h.remarks,
               COALESCE(u.full_name, 'System') AS changed_by_name
        FROM status_history h LEFT JOIN users u ON u.user_id = h.changed_by
        WHERE h.ticket_id = :id ORDER BY h.changed_at, h.history_id"""),
        {"id": ticket_id}).mappings().all()

    assignments = db.session.execute(text("""
        SELECT a.assignment_id, a.assigned_at, a.is_current,
               tech.full_name AS technician_name, adm.full_name AS assigned_by_name
        FROM ticket_assignments a
        JOIN users tech ON tech.user_id = a.technician_id
        LEFT JOIN users adm ON adm.user_id = a.assigned_by
        WHERE a.ticket_id = :id ORDER BY a.assigned_at, a.assignment_id"""),
        {"id": ticket_id}).mappings().all()

    fb = Feedback.query.filter_by(ticket_id=ticket_id).first()
    return jsonify(
        ticket=summary(ticket_id),
        history=[dict(h) for h in history],
        assignments=[dict(a) for a in assignments],
        feedback=({"rating": fb.rating, "comments": fb.comments, "submitted_at": fb.submitted_at}
                  if fb else None),
    )


# ---------------------------------------------------------------- update / close

@bp.patch("/tickets/<int:ticket_id>")
@login_required
def update_ticket(ticket_id):
    ticket = load_ticket(ticket_id)
    check_can_view(ticket)
    data = get_json()
    role = g.user.role_name
    set_actor()

    def apply_details(allow_priority):
        if "title" in data:
            ticket.title = get_str(data, "title", 150)
        if "description" in data:
            ticket.description = get_str(data, "description", 2000)
        if "category_id" in data:
            ticket.category_id = _existing(Category, get_int(data, "category_id"), "category")
        if "location_id" in data:
            ticket.location_id = _existing(Location, get_int(data, "location_id"), "location")
        if allow_priority and "priority_id" in data:
            ticket.priority_id = _existing(PriorityLevel, get_int(data, "priority_id"), "priority")

    if role == "Technician":
        # A technician's only job here is to mark their own ticket as resolved.
        if set(data) - {"status"} or data.get("status") != "Resolved":
            raise ApiError("Technicians can only mark a ticket as Resolved.", 403)
        if ticket.status != "Assigned":
            raise ApiError(f"A {ticket.status} ticket can't be marked as resolved.", 409)
        ticket.status = "Resolved"
        notify(ticket.user_id, ticket,
               f"Your ticket #{ticket.ticket_id} was marked resolved. Please leave feedback.")

    elif role == "Student":
        if ticket.user_id != g.user.user_id:
            raise ApiError("Ticket not found.", 404)
        if set(data) - {"title", "description", "category_id", "location_id"}:
            raise ApiError("You can only edit the title, description, category and location.", 403)
        if ticket.status not in ("Open", "Escalated"):
            raise ApiError("A ticket can't be edited once a technician has picked it up.", 409)
        apply_details(allow_priority=False)

    else:  # Admin
        apply_details(allow_priority=True)
        if "status" in data:
            new_status = data["status"]
            if new_status not in ("Resolved", "Closed"):
                raise ApiError("Admins can set a ticket to Resolved or Closed here; "
                               "use Assign to hand it to a technician.")
            if ticket.status == "Closed":
                raise ApiError("This ticket is already closed.", 409)
            ticket.status = new_status

    db.session.commit()
    return jsonify(ticket=summary(ticket_id))


def _existing(model, pk, label):
    if db.session.get(model, pk) is None:
        raise ApiError(f"Unknown {label}.")
    return pk


@bp.delete("/tickets/<int:ticket_id>")
@roles_required("Admin")
def close_ticket(ticket_id):
    """Tickets are never really deleted; 'deleting' one closes it so history survives."""
    ticket = load_ticket(ticket_id)
    if ticket.status == "Closed":
        raise ApiError("This ticket is already closed.", 409)
    set_actor()
    ticket.status = "Closed"
    db.session.commit()
    return jsonify(ticket=summary(ticket_id))


# ---------------------------------------------------------------- assign (transaction)

@bp.get("/technicians")
@roles_required("Admin")
def technicians():
    """Active technicians with their current load. If ticket_id is given the list is
    ordered so the best fit (same category, same block, lightest load) comes first."""
    ticket_id = request.args.get("ticket_id", type=int)
    category_id = block = None
    if ticket_id:
        ticket = load_ticket(ticket_id)
        category_id = ticket.category_id
        block = db.session.get(Location, ticket.location_id).block_name

    rows = db.session.execute(text("""
        SELECT u.user_id, u.full_name, u.specialty_category_id, c.category_name AS specialty,
               u.assigned_block,
               COUNT(t.ticket_id) FILTER (WHERE t.status IN ('Assigned', 'Escalated')) AS open_load
        FROM users u
        JOIN roles r ON r.role_id = u.role_id AND r.role_name = 'Technician'
        LEFT JOIN categories c ON c.category_id = u.specialty_category_id
        LEFT JOIN ticket_assignments ta ON ta.technician_id = u.user_id AND ta.is_current
        LEFT JOIN tickets t ON t.ticket_id = ta.ticket_id
        WHERE u.is_active
        GROUP BY u.user_id, u.full_name, u.specialty_category_id, c.category_name, u.assigned_block
        """)).mappings().all()

    out = []
    for r in rows:
        item = dict(r)
        item["matches_category"] = category_id is not None and r["specialty_category_id"] == category_id
        item["matches_block"] = block is not None and r["assigned_block"] == block
        out.append(item)
    out.sort(key=lambda x: (-(x["matches_category"] * 2 + x["matches_block"]), x["open_load"],
                            x["full_name"]))
    return jsonify(items=out)


@bp.post("/tickets/<int:ticket_id>/assign")
@roles_required("Admin")
def assign_ticket(ticket_id):
    """One transaction: retire the old assignment, add the new one, set status, notify.
    Any failure rolls the whole thing back."""
    data = get_json()
    tech_id = get_int(data, "technician_id")
    ticket = load_ticket(ticket_id)
    if ticket.status in ("Resolved", "Closed"):
        raise ApiError(f"A {ticket.status} ticket can't be assigned.", 409)

    tech = db.session.get(User, tech_id)
    if tech is None or tech.role_name != "Technician" or not tech.is_active:
        raise ApiError("Pick an active technician.")

    current = TicketAssignment.query.filter_by(ticket_id=ticket_id, is_current=True).first()
    if current and current.technician_id == tech_id:
        raise ApiError("This ticket is already assigned to that technician.", 409)

    set_actor()
    if current:
        current.is_current = False
        db.session.flush()  # free the "one current assignment" slot before inserting
    db.session.add(TicketAssignment(ticket_id=ticket_id, technician_id=tech_id,
                                    assigned_by=g.user.user_id))
    if ticket.status != "Assigned":
        ticket.status = "Assigned"
    db.session.add(Notification(user_id=tech_id, ticket_id=ticket_id,
                                message=f"Ticket #{ticket_id} was assigned to you: {ticket.title[:80]}"))
    notify(ticket.user_id, ticket, f"Your ticket #{ticket_id} was assigned to {tech.full_name}.")
    if current:
        notify(current.technician_id, ticket, f"Ticket #{ticket_id} was reassigned to someone else.")
    db.session.commit()
    return jsonify(ticket=summary(ticket_id))


# ---------------------------------------------------------------- feedback

@bp.post("/tickets/<int:ticket_id>/feedback")
@roles_required("Student")
def leave_feedback(ticket_id):
    ticket = load_ticket(ticket_id)
    if ticket.user_id != g.user.user_id:
        raise ApiError("Ticket not found.", 404)
    if ticket.status != "Resolved":
        raise ApiError("Feedback can be left once the ticket is resolved.", 409)

    data = get_json()
    rating = get_int(data, "rating")
    if not 1 <= rating <= 5:
        raise ApiError("Rating must be between 1 and 5.")
    comments = get_str(data, "comments", 500, required=False)

    set_actor()
    db.session.add(Feedback(ticket_id=ticket_id, rating=rating, comments=comments))
    ticket.status = "Closed"
    tech_id = current_technician_id(ticket_id)
    if tech_id:
        notify(tech_id, ticket, f"Ticket #{ticket_id} got a {rating}/5 rating.")
    db.session.commit()
    return jsonify(ticket=summary(ticket_id)), 201
