"""WattWise Flask application entry point."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request

from auth.security import current_user
from api.account_routes import account_api
from api.auth_routes import auth_api
from api.routes import api
from storage.database import init_database


def _local_signing_key(instance_path: str) -> str:
    # Reuse a local key across restarts so existing JWT sessions stay verifiable.
    key_path = Path(instance_path) / "wattwise.secret"
    key_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        return key_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        key = secrets.token_urlsafe(48)
        try:
            file_descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            return key_path.read_text(encoding="utf-8").strip()
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as secret_file:
            secret_file.write(key)
        return key


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    local_key = os.getenv("WATTWISE_SECRET_KEY") or _local_signing_key(app.instance_path)
    app.config.from_mapping(
        MAX_CONTENT_LENGTH=256 * 1024,
        DATABASE_PATH=os.getenv("WATTWISE_DATABASE_PATH", str(Path(app.instance_path) / "wattwise.sqlite3")),
        SECRET_KEY=local_key,
        JWT_SECRET_KEY=os.getenv("WATTWISE_JWT_SECRET", local_key),
        JWT_COOKIE_NAME="wattwise_access",
        JWT_ACCESS_MAX_AGE=8 * 60 * 60,
        JWT_COOKIE_SECURE=os.getenv("WATTWISE_COOKIE_SECURE", "0") == "1",
        LLAMA_BASE_URL=os.getenv("LLAMA_BASE_URL", "http://127.0.0.1:8080/v1"),
        LLAMA_MODEL=os.getenv("LLAMA_MODEL", "Qwen/Qwen3-0.6B-GGUF:Q8_0"),
        LLAMA_TIMEOUT_SECONDS=float(os.getenv("LLAMA_TIMEOUT_SECONDS", "90")),
    )
    if test_config:
        app.config.update(test_config)

    app.register_blueprint(api, url_prefix="/api")
    app.register_blueprint(auth_api, url_prefix="/api")
    app.register_blueprint(account_api, url_prefix="/api")
    init_database(app)

    @app.get("/")
    def home():
        user = current_user()
        if user:
            if user.get("preferred_mode"):
                return redirect("/" + user["preferred_mode"])
            return redirect("/onboarding")
        return render_template("index.html")

    @app.get("/prepaid")
    def prepaid_page():
        user = current_user()
        if not user:
            return redirect("/login")
        if not user.get("preferred_mode"):
            return redirect("/onboarding")
        if user["preferred_mode"] != "prepaid":
            return redirect("/" + user["preferred_mode"])
        return render_template("prepaid.html")

    @app.get("/postpaid")
    def postpaid_page():
        user = current_user()
        if not user:
            return redirect("/login")
        if not user.get("preferred_mode"):
            return redirect("/onboarding")
        if user["preferred_mode"] != "postpaid":
            return redirect("/" + user["preferred_mode"])
        return render_template("postpaid.html")

    @app.get("/login")
    def login_page():
        user = current_user()
        if user:
            return redirect("/" + user["preferred_mode"] if user.get("preferred_mode") else "/onboarding")
        return render_template("login.html")

    @app.get("/onboarding")
    def onboarding_page():
        user = current_user()
        if not user:
            return redirect("/login")
        if user.get("preferred_mode") and not request.args.get("edit"):
            return redirect("/" + user["preferred_mode"])
        return render_template("onboarding.html")

    @app.get("/account")
    def account_page():
        if not current_user():
            return redirect("/login")
        return render_template("account.html")

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify({"success": False, "error": {
            "code": "REQUEST_TOO_LARGE",
            "message": "This request is larger than WattWise accepts.",
            "details": [],
        }}), 413

    @app.errorhandler(500)
    def internal_error(_error):
        return jsonify({"success": False, "error": {
            "code": "INTERNAL_ERROR",
            "message": "WattWise could not complete that request.",
            "details": [],
        }}), 500

    return app


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", "5000"))
    create_app().run(host=host, port=port, debug=os.getenv("FLASK_DEBUG") == "1")

