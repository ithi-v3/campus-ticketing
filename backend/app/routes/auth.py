import re

from flask import Blueprint, g, jsonify

from ..errors import ApiError
from ..extensions import db
from ..models import Role, User
from ..security import burn_time, check_password, hash_password, login_required, make_token
from ..utils import get_json, get_str

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email(raw):
    email = (raw or "").strip().lower()
    if not EMAIL_RE.match(email) or len(email) > 120:
        raise ApiError("Enter a valid email address.")
    return email


def validate_password(password):
    if not isinstance(password, str) or not (8 <= len(password) <= 64):
        raise ApiError("Password must be 8 to 64 characters.")
    if password.isalpha() or password.isdigit():
        raise ApiError("Password should mix letters with numbers or symbols.")
    return password


@bp.post("/signup")
def signup():
    data = get_json()
    full_name = get_str(data, "full_name", 100)
    email = validate_email(data.get("email"))
    password = validate_password(data.get("password"))
    phone = get_str(data, "phone", 20, required=False)

    if User.query.filter_by(email=email).first():
        raise ApiError("An account with this email already exists.", 409)

    # Whatever "role" the client sends is ignored: public signup is always a Student.
    # Technicians and admins are created by an admin from the Users page.
    role = Role.query.filter_by(role_name="Student").one()
    user = User(full_name=full_name, email=email, phone=phone,
                password_hash=hash_password(password), role_id=role.role_id)
    db.session.add(user)
    db.session.commit()
    return jsonify(token=make_token(user), user=user.to_dict()), 201


@bp.post("/login")
def login():
    data = get_json()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not isinstance(password, str):
        raise ApiError("Email or password is wrong.", 401)

    user = User.query.filter_by(email=email).first()
    if user is None:
        burn_time()
        raise ApiError("Email or password is wrong.", 401)
    if not check_password(password, user.password_hash):
        raise ApiError("Email or password is wrong.", 401)
    if not user.is_active:
        raise ApiError("This account has been deactivated. Contact an admin.", 403)
    return jsonify(token=make_token(user), user=user.to_dict())


@bp.post("/logout")
@login_required
def logout():
    # Tokens are stateless; the client just throws its copy away.
    return jsonify(ok=True)


@bp.get("/me")
@login_required
def me():
    return jsonify(user=g.user.to_dict())
