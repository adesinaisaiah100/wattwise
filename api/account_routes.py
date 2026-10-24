"""Authenticated, user-scoped appliance profiles and analysis history."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from flask import Blueprint, g, jsonify, request

from auth.security import require_auth
from core.validation import InputError, object_payload, validate_appliances
from services.analysis import analyze_case
from storage.database import connect


account_api = Blueprint("account_api", __name__)
VALID_MODES = {"prepaid", "postpaid"}


def _error(code: str, message: str, status: int):
    return jsonify({"success": False, "error": {
        "code": code, "message": message, "details": [],
    }}), status


@account_api.get("/account/preferences")
@require_auth
def get_preferences():
    return jsonify({"success": True, "data": {
        "customer_type": g.current_user.get("preferred_mode"),
    }, "warnings": []})


@account_api.put("/account/preferences")
@require_auth
def put_preferences():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or payload.get("customer_type") not in VALID_MODES:
        return _error("VALIDATION_ERROR", "Choose prepaid or postpaid to set up your WattWise account.", 422)
    customer_type = payload["customer_type"]
    updated_at = datetime.now(timezone.utc).isoformat()
    connection = connect()
    try:
        connection.execute(
            "INSERT INTO household_preferences (user_id, customer_type, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET customer_type = excluded.customer_type, updated_at = excluded.updated_at",
            (g.current_user["id"], customer_type, updated_at),
        )
        connection.commit()
    finally:
        connection.close()
    return jsonify({"success": True, "data": {"customer_type": customer_type}, "warnings": []})


@account_api.get("/account/appliances")
@require_auth
def get_appliances():
    connection = connect()
    try:
        row = connection.execute(
            "SELECT appliances_json, updated_at FROM appliance_profiles WHERE user_id = ?",
            (g.current_user["id"],),
        ).fetchone()
    finally:
        connection.close()
    profile = {"appliances": [], "updated_at": None} if row is None else {
        "appliances": json.loads(row["appliances_json"]), "updated_at": row["updated_at"],
    }
    return jsonify({"success": True, "data": profile, "warnings": []})


@account_api.put("/account/appliances")
@require_auth
def put_appliances():
    try:
        payload = object_payload(request.get_json(silent=True))
        appliances = validate_appliances(payload.get("appliances"))
    except InputError as exc:
        return _error("VALIDATION_ERROR", str(exc), 422)
    updated_at = datetime.now(timezone.utc).isoformat()
    connection = connect()
    try:
        connection.execute(
            "INSERT INTO appliance_profiles (user_id, appliances_json, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET appliances_json = excluded.appliances_json, updated_at = excluded.updated_at",
            (g.current_user["id"], json.dumps(appliances, separators=(",", ":")), updated_at),
        )
        connection.commit()
    finally:
        connection.close()
    return jsonify({"success": True, "data": {"appliances": appliances, "updated_at": updated_at}, "warnings": []})


@account_api.post("/account/history")
@require_auth
def save_history():
    try:
        payload = object_payload(request.get_json(silent=True))
        mode = payload.get("mode")
        selected_mode = g.current_user.get("preferred_mode")
        if selected_mode is None:
            return _error("HOUSEHOLD_SETUP_REQUIRED", "Choose prepaid or postpaid before saving an analysis.", 409)
        if mode != selected_mode:
            return _error("SERVICE_TYPE_MISMATCH", "This account is set up for a different electricity service type.", 403)
        case = object_payload(payload.get("case"))
        normalized, result = analyze_case(mode, case)
    except InputError as exc:
        return _error("VALIDATION_ERROR", str(exc), 422)
    entry = {
        "id": str(uuid4()),
        "user_id": g.current_user["id"],
        "mode": mode,
        "request_json": json.dumps(normalized, separators=(",", ":")),
        "result_json": json.dumps(result, separators=(",", ":")),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    connection = connect()
    try:
        connection.execute(
            "INSERT INTO analysis_history (id, user_id, mode, request_json, result_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (entry["id"], entry["user_id"], entry["mode"], entry["request_json"],
             entry["result_json"], entry["created_at"]),
        )
        connection.commit()
    finally:
        connection.close()
    return jsonify({"success": True, "data": {"id": entry["id"], "mode": mode,
                                                "created_at": entry["created_at"], "result": result},
                    "warnings": []}), 201


@account_api.get("/account/history")
@require_auth
def get_history():
    selected_mode = g.current_user.get("preferred_mode")
    if selected_mode is None:
        return _error("HOUSEHOLD_SETUP_REQUIRED", "Choose prepaid or postpaid to view your saved analyses.", 409)
    raw_limit = request.args.get("limit", "25")
    try:
        limit = int(raw_limit)
    except ValueError:
        return _error("VALIDATION_ERROR", "History limit must be a whole number.", 422)
    if not 1 <= limit <= 100:
        return _error("VALIDATION_ERROR", "History limit must be between 1 and 100.", 422)
    connection = connect()
    try:
        rows = connection.execute(
            "SELECT id, mode, request_json, result_json, created_at FROM analysis_history "
            "WHERE user_id = ? AND mode = ? ORDER BY created_at DESC LIMIT ?",
            (g.current_user["id"], selected_mode, limit),
        ).fetchall()
    finally:
        connection.close()
    entries = [{"id": row["id"], "mode": row["mode"],
                "request": json.loads(row["request_json"]),
                "result": json.loads(row["result_json"]),
                "created_at": row["created_at"]} for row in rows]
    return jsonify({"success": True, "data": {"entries": entries}, "warnings": []})
