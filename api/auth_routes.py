"""Account registration and JWT login routes."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

import jwt
from flask import Blueprint, current_app, jsonify, make_response, request

from auth.security import current_user, hash_password, issue_access_token, password_matches
from auth.rate_limit import clear_login_failures, login_retry_after, record_login_failure
from storage.database import connect


auth_api = Blueprint("auth_api", __name__)
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _body() -> dict:
    if not request.is_json:
        raise ValueError("Send a JSON object.")
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValueError("Send a valid JSON object.")
    return body


def _error(code: str, message: str, status: int):
    return jsonify({"success": False, "error": {
        "code": code, "message": message, "details": [],
    }}), status


def _credentials(body: dict) -> tuple[str, str]:
    email = body.get("email")
    password = body.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        raise ValueError("Enter an email address and password.")
    email = email.strip().lower()
    if len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
        raise ValueError("Enter a valid email address.")
    if len(password) < 8 or len(password) > 128:
        raise ValueError("Password must be between 8 and 128 characters.")
    return email, password


def _auth_success(user: dict, status: int = 200):
    token = issue_access_token(user["id"])
    response = make_response(jsonify({
        "success": True,
        "data": {"user": {"id": user["id"], "email": user["email"],
                            "preferred_mode": user.get("preferred_mode")}},
        "warnings": [],
    }), status)
    response.set_cookie(
        current_app.config["JWT_COOKIE_NAME"], token,
        max_age=current_app.config["JWT_ACCESS_MAX_AGE"],
        httponly=True,
        secure=current_app.config["JWT_COOKIE_SECURE"],
        samesite="Strict",
        path="/",
    )
    return response


@auth_api.post("/auth/register")
def register():
    try:
        email, password = _credentials(_body())
    except ValueError as exc:
        return _error("VALIDATION_ERROR", str(exc), 422)
    user = {
        "id": str(uuid4()),
        "email": email,
        "password_hash": hash_password(password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    connection = connect()
    try:
        connection.execute(
            "INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (user["id"], user["email"], user["password_hash"], user["created_at"]),
        )
        connection.commit()
    except sqlite3.IntegrityError:
        return _error("EMAIL_ALREADY_REGISTERED", "An account with this email already exists.", 409)
    finally:
        connection.close()
    return _auth_success(user, 201)


@auth_api.post("/auth/login")
def login():
    try:
        email, password = _credentials(_body())
    except ValueError as exc:
        return _error("VALIDATION_ERROR", str(exc), 422)
    client_key = request.remote_addr or "unknown"
    retry_after = login_retry_after(client_key)
    if retry_after is not None:
        response, status = _error("LOGIN_RATE_LIMITED", "Too many failed attempts. Try again later.", 429)
        response.headers["Retry-After"] = str(retry_after)
        return response, status
    connection = connect()
    try:
        row = connection.execute(
            "SELECT users.id, users.email, users.password_hash, household_preferences.customer_type AS preferred_mode "
            "FROM users LEFT JOIN household_preferences ON household_preferences.user_id = users.id "
            "WHERE users.email = ?", (email,)
        ).fetchone()
    finally:
        connection.close()
    if row is None or not password_matches(row["password_hash"], password):
        record_login_failure(client_key)
        return _error("INVALID_CREDENTIALS", "Email or password is incorrect.", 401)
    clear_login_failures(client_key)
    return _auth_success(dict(row))


@auth_api.post("/auth/logout")
def logout():
    response = make_response(jsonify({"success": True, "data": {"logged_out": True}, "warnings": []}))
    response.delete_cookie(current_app.config["JWT_COOKIE_NAME"], path="/", samesite="Strict")
    return response


@auth_api.get("/auth/me")
def me():
    user = current_user()
    if user is None:
        return _error("AUTH_REQUIRED", "Sign in to continue.", 401)
    return jsonify({"success": True, "data": {"user": user}, "warnings": []})
