import datetime
from functools import wraps

import bcrypt
import jwt
from flask import current_app, g, request

from .errors import ApiError
from .extensions import db
from .models import User

# Used so a login attempt for an unknown email takes about as long as a real one.
_DUMMY_HASH = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt(12))


def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")


def check_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def burn_time():
    bcrypt.checkpw(b"x", _DUMMY_HASH)


def make_token(user):
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": str(user.user_id),  # PyJWT requires the subject to be a string
        "role": user.role_name,
        "iat": now,
        "exp": now + datetime.timedelta(hours=current_app.config["JWT_HOURS"]),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm="HS256")


def _user_from_request():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise ApiError("Please log in.", 401)
    token = header[7:]
    try:
        payload = jwt.decode(token, current_app.config["JWT_SECRET"], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise ApiError("Your session has expired. Please log in again.", 401)
    except jwt.InvalidTokenError:
        raise ApiError("Invalid login token.", 401)
    user = db.session.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise ApiError("This account is not available.", 401)
    return user


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        g.user = _user_from_request()
        return fn(*args, **kwargs)

    return wrapper


def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            g.user = _user_from_request()
            if g.user.role_name not in roles:
                raise ApiError("You don't have access to this.", 403)
            return fn(*args, **kwargs)

        return wrapper

    return decorator
