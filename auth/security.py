"""Password hashing and short-lived JWT authentication."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import wraps
from uuid import uuid4

import jwt
from flask import current_app, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from storage.database import connect


ISSUER = "wattwise-local"
TOKEN_LIFETIME = timedelta(hours=8)


def hash_password(password: str) -> str:
    return generate_password_hash(password, method="scrypt")


def password_matches(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)


def issue_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": user_id,
        "iss": ISSUER,
        "iat": now,
        "exp": now + TOKEN_LIFETIME,
        "jti": str(uuid4()),
        "typ": "access",
    }
    return jwt.encode(claims, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")


def _request_token() -> str | None:
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip() or None
    return request.cookies.get(current_app.config["JWT_COOKIE_NAME"])


def current_user() -> dict | None:
    token = _request_token()
    if not token:
        return None
    try:
        claims = jwt.decode(
            token,
            current_app.config["JWT_SECRET_KEY"],
            algorithms=["HS256"],
            issuer=ISSUER,
            options={"require": ["sub", "exp", "iat", "iss", "typ"]},
        )
        if claims.get("typ") != "access":
            return None
    except jwt.InvalidTokenError:
        return None
    connection = connect()
    try:
        row = connection.execute(
            "SELECT users.id, users.email, users.created_at, household_preferences.customer_type AS preferred_mode "
            "FROM users LEFT JOIN household_preferences ON household_preferences.user_id = users.id "
            "WHERE users.id = ?", (claims["sub"],)
        ).fetchone()
    finally:
        connection.close()
    return dict(row) if row else None


def require_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user is None:
            return jsonify({"success": False, "error": {
                "code": "AUTH_REQUIRED",
                "message": "Sign in to access this account data.",
                "details": [],
            }}), 401
        g.current_user = user
        return view(*args, **kwargs)
    return wrapped


def require_mode(expected_mode: str):
    """Limit an authenticated account to the service type it selected."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = getattr(g, "current_user", None)
            if user is None:
                user = current_user()
                if user is None:
                    return jsonify({"success": False, "error": {
                        "code": "AUTH_REQUIRED", "message": "Sign in to continue.", "details": [],
                    }}), 401
                g.current_user = user
            selected_mode = user.get("preferred_mode")
            if selected_mode is None:
                return jsonify({"success": False, "error": {
                    "code": "HOUSEHOLD_SETUP_REQUIRED",
                    "message": "Choose prepaid or postpaid to finish setting up your household.",
                    "details": [],
                }}), 409
            if selected_mode != expected_mode:
                return jsonify({"success": False, "error": {
                    "code": "SERVICE_TYPE_MISMATCH",
                    "message": "This account is set up for a different electricity service type.",
                    "details": [],
                }}), 403
            return view(*args, **kwargs)
        return wrapped
    return decorator
