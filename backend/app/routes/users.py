from flask import Blueprint, g, jsonify, request

from ..errors import ApiError
from ..extensions import db
from ..models import Category, Role, User
from ..security import hash_password, roles_required
from ..utils import get_int, get_json, get_str
from .auth import validate_email, validate_password

bp = Blueprint("users", __name__, url_prefix="/api/users")


def _role(name):
    role = Role.query.filter_by(role_name=name).first()
    if role is None:
        raise ApiError("Role must be Student, Technician or Admin.")
    return role


def _technician_fields(user, data):
    if "specialty_category_id" in data:
        cat_id = get_int(data, "specialty_category_id", required=False)
        if cat_id is not None and db.session.get(Category, cat_id) is None:
            raise ApiError("Unknown category.")
        user.specialty_category_id = cat_id
    if "assigned_block" in data:
        user.assigned_block = get_str(data, "assigned_block", 60, required=False)


@bp.get("")
@roles_required("Admin")
def list_users():
    query = User.query.join(Role)
    role = request.args.get("role")
    if role:
        query = query.filter(Role.role_name == role)
    users = query.order_by(User.full_name).all()
    return jsonify(items=[u.to_dict() for u in users])


@bp.post("")
@roles_required("Admin")
def create_user():
    data = get_json()
    email = validate_email(data.get("email"))
    if User.query.filter_by(email=email).first():
        raise ApiError("An account with this email already exists.", 409)
    user = User(
        full_name=get_str(data, "full_name", 100),
        email=email,
        password_hash=hash_password(validate_password(data.get("password"))),
        role_id=_role(get_str(data, "role", 20)).role_id,
        phone=get_str(data, "phone", 20, required=False),
    )
    _technician_fields(user, data)
    db.session.add(user)
    db.session.commit()
    return jsonify(user=user.to_dict()), 201


@bp.patch("/<int:user_id>")
@roles_required("Admin")
def update_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        raise ApiError("User not found.", 404)
    data = get_json()

    if "role" in data:
        new_role = _role(get_str(data, "role", 20))
        if user.user_id == g.user.user_id and new_role.role_name != "Admin":
            raise ApiError("You can't remove your own admin access.", 400)
        user.role_id = new_role.role_id
    if "is_active" in data:
        if user.user_id == g.user.user_id and not data["is_active"]:
            raise ApiError("You can't deactivate your own account.", 400)
        user.is_active = bool(data["is_active"])
    if "full_name" in data:
        user.full_name = get_str(data, "full_name", 100)
    if "phone" in data:
        user.phone = get_str(data, "phone", 20, required=False)
    _technician_fields(user, data)

    db.session.commit()
    return jsonify(user=user.to_dict())
