"""ORM models. The tables themselves are created by database/01_schema.sql,
these classes just map onto them."""
from .extensions import db


class Role(db.Model):
    __tablename__ = "roles"
    role_id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(20), nullable=False, unique=True)


class Category(db.Model):
    __tablename__ = "categories"
    category_id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(200))


class Location(db.Model):
    __tablename__ = "locations"
    location_id = db.Column(db.Integer, primary_key=True)
    block_name = db.Column(db.String(60), nullable=False)
    room = db.Column(db.String(30), nullable=False)
    location_type = db.Column(db.String(20), nullable=False)


class PriorityLevel(db.Model):
    __tablename__ = "priority_levels"
    priority_id = db.Column(db.Integer, primary_key=True)
    priority_name = db.Column(db.String(20), nullable=False, unique=True)
    rank = db.Column(db.Integer, nullable=False, unique=True)
    escalation_days = db.Column(db.Integer, nullable=False, default=3)


class User(db.Model):
    __tablename__ = "users"
    user_id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.role_id"), nullable=False)
    phone = db.Column(db.String(20))
    specialty_category_id = db.Column(db.Integer, db.ForeignKey("categories.category_id"))
    assigned_block = db.Column(db.String(60))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    role = db.relationship("Role")
    specialty = db.relationship("Category")

    @property
    def role_name(self):
        return self.role.role_name

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "full_name": self.full_name,
            "email": self.email,
            "role": self.role_name,
            "phone": self.phone,
            "specialty_category_id": self.specialty_category_id,
            "specialty": self.specialty.category_name if self.specialty else None,
            "assigned_block": self.assigned_block,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }


class Ticket(db.Model):
    __tablename__ = "tickets"
    ticket_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.category_id"), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey("locations.location_id"), nullable=False)
    priority_id = db.Column(db.Integer, db.ForeignKey("priority_levels.priority_id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Open")
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now())
    resolved_at = db.Column(db.DateTime)

    reporter = db.relationship("User", foreign_keys=[user_id])


class TicketAssignment(db.Model):
    __tablename__ = "ticket_assignments"
    assignment_id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.ticket_id"), nullable=False)
    technician_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    assigned_by = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    assigned_at = db.Column(db.DateTime, server_default=db.func.now())
    is_current = db.Column(db.Boolean, nullable=False, default=True)


class StatusHistory(db.Model):
    __tablename__ = "status_history"
    history_id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.ticket_id"), nullable=False)
    old_status = db.Column(db.String(20))
    new_status = db.Column(db.String(20), nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    changed_at = db.Column(db.DateTime, server_default=db.func.now())
    remarks = db.Column(db.String(255))


class Feedback(db.Model):
    __tablename__ = "feedback"
    feedback_id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.ticket_id"), nullable=False, unique=True)
    rating = db.Column(db.Integer, nullable=False)
    comments = db.Column(db.String(500))
    submitted_at = db.Column(db.DateTime, server_default=db.func.now())


class Notification(db.Model):
    __tablename__ = "notifications"
    notification_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.ticket_id"))
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
