"""Smoke and regression checks for deterministic WattWise behavior."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from urllib.error import URLError
import jwt

from app import create_app
from ai.adapter import ModelUnavailable, explain, generate_routine_proposal
from auth.rate_limit import reset_login_limits
from core.consumption import estimate_household
from core.validation import InputError, validate_appliances
from services.analysis import prepare_postpaid, prepare_prepaid
from services.planning import create_verified_plan


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "phases" / "contracts"


def read_fixture(name: str) -> dict:
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, limit: int = -1) -> bytes:
        return self.body if limit < 0 else self.body[:limit]


def fake_chat_response(content: str) -> FakeResponse:
    return FakeResponse(json.dumps({"choices": [{"message": {"content": content}}]}).encode())


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.result = {
            "mode": "prepaid",
            "estimated_daily_consumption_kwh": 2.1,
            "routine_options": [{"id": "routine-50", "label": "Lower flexible use", "changes": []}],
        }

    def test_validates_json_and_only_returns_approved_routine_ids(self):
        content = json.dumps({
            "summary": "This is an estimate.",
            "key_points": ["Review flexible appliance use."],
            "recommended_routine_ids": ["unknown", "routine-50"],
            "cautions": [],
            "next_steps": [],
        })
        with patch("ai.adapter.urlopen", return_value=fake_chat_response(content)) as mocked:
            result = explain(base_url="http://127.0.0.1:8080/v1", model="qwen", timeout=1,
                             mode="prepaid", result=self.result)
        request = mocked.call_args.args[0]
        sent = json.loads(request.data.decode())
        self.assertEqual(sent["reasoning_effort"], "none")
        self.assertEqual(result["recommended_routine_ids"], ["routine-50"])
        self.assertEqual(result["summary"], "This is an estimate.")

    def test_model_timeout_and_connection_errors_are_safe(self):
        for failure in (TimeoutError("slow"), URLError("offline")):
            with self.subTest(failure=type(failure).__name__), patch("ai.adapter.urlopen", side_effect=failure):
                with self.assertRaises(ModelUnavailable):
                    explain(base_url="http://127.0.0.1:8080/v1", model="qwen", timeout=0.01,
                            mode="prepaid", result=self.result)

    def test_invalid_model_json_is_rejected(self):
        with patch("ai.adapter.urlopen", return_value=fake_chat_response("not-json")):
            with self.assertRaises(ModelUnavailable):
                explain(base_url="http://127.0.0.1:8080/v1", model="qwen", timeout=1,
                        mode="prepaid", result=self.result)

    def test_oversized_model_response_is_rejected(self):
        large_content = json.dumps({"summary": "x" * 130_000})
        with patch("ai.adapter.urlopen", return_value=fake_chat_response(large_content)):
            with self.assertRaises(ModelUnavailable):
                explain(base_url="http://127.0.0.1:8080/v1", model="qwen", timeout=1,
                        mode="prepaid", result=self.result)

    def test_ai_plan_proposal_is_requested_as_json(self):
        content = json.dumps({
            "title": "Evening routine", "summary": "Run flexible appliances for fewer hours.",
            "schedule": [{"appliance_id": "fan-1", "hours_per_use_day": 4,
                          "uses_per_week": 7, "reason": "Shorten fan use at night."}],
            "tips": ["Switch the fan off when leaving the room."],
        })
        with patch("ai.adapter.urlopen", return_value=fake_chat_response(content)) as mocked:
            result = generate_routine_proposal(
                base_url="http://127.0.0.1:8080/v1", model="qwen", timeout=1,
                mode="prepaid", goal={"type": "make_prepaid_units_last", "target_days": 14},
                appliances=[{"id": "fan-1", "label": "Fan", "quantity": 1,
                             "essential": False, "category": "cooling",
                             "energy_input": {"method": "power_and_schedule", "power_watts": 75},
                             "routine": {"hours_per_use_day": 8, "uses_per_week": 7}}],
                analysis=self.result,
            )
        sent = json.loads(mocked.call_args.args[0].data.decode())
        self.assertEqual(sent["response_format"], {"type": "json_object"})
        self.assertEqual(result["schedule"][0]["hours_per_use_day"], 4)


class CalculationTests(unittest.TestCase):
    def test_prepaid_fixture_math(self):
        request = read_fixture("prepaid-request.example.json")
        normalized, result = prepare_prepaid(request)
        self.assertAlmostEqual(result["estimated_daily_consumption_kwh"], 2.1)
        self.assertAlmostEqual(result["estimated_target_consumption_kwh"], 29.4)
        self.assertAlmostEqual(result["units_after_target_kwh"], 30.6)
        self.assertAlmostEqual(result["projected_duration_days"], 60 / 2.1)
        self.assertTrue(result["target_met"])
        self.assertEqual(normalized["available_units_kwh"], 60)

    def test_postpaid_fixture_math(self):
        request = read_fixture("postpaid-request.example.json")
        _, result = prepare_postpaid(request)
        self.assertAlmostEqual(result["estimated_household_kwh"], 63)
        self.assertEqual(result["billed_consumption"]["units_kwh"], 100)
        self.assertAlmostEqual(result["comparisons"][0]["difference_kwh"], -37)
        self.assertAlmostEqual(result["expected_billed_energy_charge_ngn"], 10000)
        self.assertEqual(result["total_amount_due_ngn"], 12500)

    def test_invalid_appliance_schedule_is_rejected(self):
        request = read_fixture("prepaid-request.example.json")
        request["appliances"][0]["routine"]["hours_per_use_day"] = 25
        with self.assertRaises(InputError):
            validate_appliances(request["appliances"])

    def test_energy_estimate_is_independent_of_flask(self):
        request = read_fixture("prepaid-request.example.json")
        appliances = validate_appliances(request["appliances"])
        result = estimate_household(appliances, 30)
        self.assertAlmostEqual(result["estimated_consumption_kwh"], 63)

    def test_verified_prepaid_plan_meets_target_without_changing_essentials(self):
        request = read_fixture("prepaid-request.example.json")
        request["available_units_kwh"] = 25
        appliances = validate_appliances(request["appliances"])
        _, analysis = prepare_prepaid(request)
        proposal = {"title": "Model plan", "summary": "Use flexible appliances less.",
                    "schedule": [{"appliance_id": item["id"],
                                  "hours_per_use_day": item["routine"]["hours_per_use_day"],
                                  "uses_per_week": item["routine"]["uses_per_week"],
                                  "reason": "Model suggestion."} for item in appliances],
                    "tips": []}
        plan = create_verified_plan(mode="prepaid", appliances=appliances,
                                    analysis=analysis, proposal=proposal)
        self.assertTrue(plan["goal"]["achieved"])
        self.assertLessEqual(plan["goal"]["estimated_period_kwh"], 25)
        essential_rows = [item for item in plan["schedule"] if item["essential"]]
        for row in essential_rows:
            original = next(item for item in appliances if item["id"] == row["appliance_id"])
            self.assertEqual(row["hours_per_use_day"], original["routine"]["hours_per_use_day"])
            self.assertEqual(row["uses_per_week"], original["routine"]["uses_per_week"])


class ApiTests(unittest.TestCase):
    def setUp(self):
        reset_login_limits()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = str(Path(self.temp_dir.name) / "test.sqlite3")
        self.client = create_app({
            "TESTING": True,
            "DATABASE_PATH": self.database_path,
            "JWT_SECRET_KEY": "test-only-signing-key-for-wattwise",
            "LLAMA_BASE_URL": "http://127.0.0.1:1/v1",
            "LLAMA_TIMEOUT_SECONDS": 0.5,
        }).test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def register(self, client, email):
        return client.post("/api/auth/register", json={"email": email, "password": "correct horse battery"})

    def sign_in(self, email="analysis@example.com", customer_type="prepaid"):
        response = self.register(self.client, email)
        self.assertEqual(response.status_code, 201)
        preferences = self.client.put("/api/account/preferences", json={"customer_type": customer_type})
        self.assertEqual(preferences.status_code, 200)
        return self.client

    def test_health_is_available_without_model(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["calculation_engine"], "ready")
        self.assertEqual(response.json["data"]["model"], "not_loaded")

    def test_prepaid_analysis_api(self):
        self.sign_in()
        response = self.client.post("/api/prepaid/analyze", json=read_fixture("prepaid-request.example.json"))
        self.assertEqual(response.status_code, 200)
        self.assertAlmostEqual(response.json["data"]["estimated_daily_consumption_kwh"], 2.1)

    def test_postpaid_analysis_api(self):
        self.sign_in(customer_type="postpaid")
        response = self.client.post("/api/postpaid/analyze", json=read_fixture("postpaid-request.example.json"))
        self.assertEqual(response.status_code, 200)
        self.assertAlmostEqual(response.json["data"]["estimated_household_kwh"], 63)

    def test_ai_plan_endpoint_uses_model_proposal_and_checks_postpaid_goal(self):
        self.sign_in(customer_type="postpaid")
        appliances = validate_appliances(read_fixture("postpaid-request.example.json")["appliances"])
        first_proposal = {"title": "Draft one", "summary": "Initial routine.",
                          "schedule": [{"appliance_id": item["id"],
                                        "hours_per_use_day": item["routine"]["hours_per_use_day"],
                                        "uses_per_week": item["routine"]["uses_per_week"],
                                        "reason": "AI routine proposal."} for item in appliances],
                          "tips": []}
        second_proposal = {**first_proposal, "title": "Draft two", "schedule": [
            {"appliance_id": item["id"],
             "hours_per_use_day": 2 if item["id"] == "fan-1" else item["routine"]["hours_per_use_day"],
             "uses_per_week": item["routine"]["uses_per_week"], "reason": "AI routine proposal."}
            for item in appliances
        ]}
        with patch("api.routes.generate_routine_proposal", side_effect=[first_proposal, second_proposal]) as mocked:
            response = self.client.post("/api/recommendations/plan", json={
                "mode": "postpaid",
                "case": {**read_fixture("postpaid-request.example.json"), "target_reduction_percent": 20},
            })
        self.assertEqual(response.status_code, 200)
        plan = response.json["data"]["plan"]
        self.assertTrue(plan["goal"]["achieved"])
        self.assertEqual(plan["goal"]["target_reduction_percent"], 20)
        self.assertLessEqual(plan["goal"]["estimated_period_kwh"], plan["goal"]["target_period_kwh"])
        self.assertEqual(plan["model_proposal_rounds"], 2)
        self.assertEqual(mocked.call_count, 2)
        self.assertEqual(len(plan["schedule"]), 3)

    def test_ai_plan_stream_sends_progress_and_verified_plan(self):
        self.sign_in(customer_type="prepaid")
        case = read_fixture("prepaid-request.example.json")
        appliances = validate_appliances(case["appliances"])
        proposal = {"title": "Routine", "summary": "A proposed schedule.",
                    "schedule": [{"appliance_id": item["id"],
                                  "hours_per_use_day": item["routine"]["hours_per_use_day"],
                                  "uses_per_week": item["routine"]["uses_per_week"],
                                  "reason": "AI routine proposal."} for item in appliances],
                    "tips": ["Review your high-use appliances."]}
        with patch("api.routes.generate_routine_proposal", return_value=proposal):
            response = self.client.post("/api/recommendations/plan/stream", json={
                "mode": "prepaid", "case": case,
            })
            response_text = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.content_type)
        events = [json.loads(line[6:]) for line in response_text.splitlines()
                  if line.startswith("data: ")]
        self.assertEqual(events[0]["type"], "progress")
        self.assertEqual(events[-1]["type"], "plan", events)
        self.assertIn("schedule", events[-1]["plan"])

    def test_missing_appliances_is_a_validation_error(self):
        self.sign_in()
        response = self.client.post("/api/prepaid/analyze", json={"target_days": 30, "available_units_kwh": 50})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json["error"]["code"], "VALIDATION_ERROR")

    def test_malformed_json_has_a_400_response(self):
        self.sign_in()
        response = self.client.post("/api/prepaid/analyze", data="{broken", content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"]["code"], "MALFORMED_JSON")

    def test_register_hashes_password_and_login_logout_work(self):
        registered = self.register(self.client, "Member@Example.com")
        self.assertEqual(registered.status_code, 201)
        self.assertIn("HttpOnly", registered.headers["Set-Cookie"])
        self.assertIn("SameSite=Strict", registered.headers["Set-Cookie"])
        self.assertNotIn("access_token", registered.json["data"])

        connection = sqlite3.connect(self.database_path)
        try:
            password_hash = connection.execute("SELECT password_hash FROM users").fetchone()[0]
        finally:
            connection.close()
        self.assertNotEqual(password_hash, "correct horse battery")
        self.assertTrue(password_hash.startswith("scrypt:"))
        self.assertEqual(self.client.get("/api/auth/me").json["data"]["user"]["email"], "member@example.com")

        bad_login = self.client.post("/api/auth/login", json={"email": "member@example.com", "password": "wrong password"})
        self.assertEqual(bad_login.status_code, 401)
        good_login = self.client.post("/api/auth/login", json={"email": "MEMBER@example.com", "password": "correct horse battery"})
        self.assertEqual(good_login.status_code, 200)
        logged_out = self.client.post("/api/auth/logout")
        self.assertEqual(logged_out.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_profiles_and_analysis_history_are_isolated_between_users(self):
        first_client = self.client
        self.assertEqual(self.register(first_client, "first@example.com").status_code, 201)
        self.assertEqual(first_client.put("/api/account/preferences", json={"customer_type": "prepaid"}).status_code, 200)
        appliances = read_fixture("prepaid-request.example.json")["appliances"]
        saved_profile = first_client.put("/api/account/appliances", json={"appliances": appliances})
        self.assertEqual(saved_profile.status_code, 200)
        self.assertEqual(len(first_client.get("/api/account/appliances").json["data"]["appliances"]), 3)
        history_response = first_client.post("/api/account/history", json={
            "mode": "prepaid", "case": read_fixture("prepaid-request.example.json"),
        })
        self.assertEqual(history_response.status_code, 201)
        self.assertEqual(len(first_client.get("/api/account/history").json["data"]["entries"]), 1)

        second_client = create_app({
            "TESTING": True,
            "DATABASE_PATH": self.database_path,
            "JWT_SECRET_KEY": "test-only-signing-key-for-wattwise",
            "LLAMA_BASE_URL": "http://127.0.0.1:1/v1",
        }).test_client()
        self.assertEqual(self.register(second_client, "second@example.com").status_code, 201)
        self.assertEqual(second_client.put("/api/account/preferences", json={"customer_type": "prepaid"}).status_code, 200)
        self.assertEqual(second_client.get("/api/account/appliances").json["data"]["appliances"], [])
        self.assertEqual(second_client.get("/api/account/history").json["data"]["entries"], [])

    def test_account_endpoints_reject_missing_or_invalid_tokens(self):
        self.assertEqual(self.client.get("/api/account/history").status_code, 401)
        response = self.client.get("/api/account/history", headers={"Authorization": "Bearer not-a-jwt"})
        self.assertEqual(response.status_code, 401)

    def test_account_endpoints_reject_expired_and_wrong_signature_tokens(self):
        self.assertEqual(self.register(self.client, "jwt-check@example.com").status_code, 201)
        user_id = self.client.get("/api/auth/me").json["data"]["user"]["id"]
        now = datetime.now(timezone.utc)
        expired = jwt.encode({
            "sub": user_id, "iss": "wattwise-local", "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1), "typ": "access",
        }, "test-only-signing-key-for-wattwise", algorithm="HS256")
        wrong_signature = jwt.encode({
            "sub": user_id, "iss": "wattwise-local", "iat": now,
            "exp": now + timedelta(hours=1), "typ": "access",
        }, "different-test-signing-key-that-is-long-enough", algorithm="HS256")
        for token in (expired, wrong_signature):
            response = self.client.get("/api/account/history", headers={"Authorization": f"Bearer {token}"})
            self.assertEqual(response.status_code, 401)

    def test_account_data_survives_recreating_the_flask_app(self):
        self.assertEqual(self.register(self.client, "restart-check@example.com").status_code, 201)
        self.assertEqual(self.client.put("/api/account/preferences", json={"customer_type": "prepaid"}).status_code, 200)
        prepaid = read_fixture("prepaid-request.example.json")
        saved = self.client.put("/api/account/appliances", json={"appliances": prepaid["appliances"]})
        self.assertEqual(saved.status_code, 200)
        history = self.client.post("/api/account/history", json={"mode": "prepaid", "case": prepaid})
        self.assertEqual(history.status_code, 201)

        restarted_client = create_app({
            "TESTING": True,
            "DATABASE_PATH": self.database_path,
            "JWT_SECRET_KEY": "test-only-signing-key-for-wattwise",
            "LLAMA_BASE_URL": "http://127.0.0.1:1/v1",
        }).test_client()
        login = restarted_client.post("/api/auth/login", json={
            "email": "restart-check@example.com", "password": "correct horse battery",
        })
        self.assertEqual(login.status_code, 200)
        self.assertEqual(len(restarted_client.get("/api/account/appliances").json["data"]["appliances"]), 3)
        self.assertEqual(len(restarted_client.get("/api/account/history").json["data"]["entries"]), 1)

    def test_preference_onboarding_and_mode_specific_access(self):
        self.assertEqual(self.register(self.client, "onboarding@example.com").status_code, 201)
        self.assertIsNone(self.client.get("/api/auth/me").json["data"]["user"]["preferred_mode"])
        self.assertEqual(self.client.put("/api/account/preferences", json={"customer_type": "postpaid"}).status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me").json["data"]["user"]["preferred_mode"], "postpaid")
        self.assertEqual(self.client.get("/postpaid").status_code, 200)
        self.assertEqual(self.client.get("/prepaid").status_code, 302)
        self.assertEqual(self.client.get("/prepaid").headers["Location"], "/postpaid")
        self.assertEqual(self.client.get("/").headers["Location"], "/postpaid")

    def test_calculation_pages_and_apis_require_login(self):
        self.assertEqual(self.client.get("/prepaid").headers["Location"], "/login")
        self.assertEqual(self.client.get("/postpaid").headers["Location"], "/login")
        self.assertEqual(self.client.get("/account").headers["Location"], "/login")
        for path in ("/api/consumption/estimate", "/api/prepaid/analyze", "/api/postpaid/analyze",
                     "/api/recommendations/explain", "/api/recommendations/explain/stream"):
            response = self.client.post(path, json={})
            self.assertEqual(response.status_code, 401, path)

    def test_calculation_endpoints_are_limited_to_selected_service_type(self):
        self.sign_in(customer_type="prepaid")
        wrong_analysis = self.client.post("/api/postpaid/analyze", json=read_fixture("postpaid-request.example.json"))
        self.assertEqual(wrong_analysis.status_code, 403)
        self.assertEqual(wrong_analysis.json["error"]["code"], "SERVICE_TYPE_MISMATCH")
        self.assertEqual(self.client.get("/postpaid").headers["Location"], "/prepaid")

    def test_streamed_explanation_returns_server_sent_events(self):
        self.sign_in()
        with patch("api.routes.stream_explanation", return_value=iter(["Your estimate is ", "about 2 kWh per day."])):
            response = self.client.post("/api/recommendations/explain/stream", json={
                "mode": "prepaid", "case": read_fixture("prepaid-request.example.json"),
            }, buffered=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.mimetype.startswith("text/event-stream"))
        self.assertIn('"type": "token"', response.get_data(as_text=True))
        self.assertIn("about 2 kWh per day.", response.get_data(as_text=True))

    def test_login_rate_limit_blocks_repeated_failed_attempts(self):
        self.register(self.client, "rate-limit@example.com")
        self.client.post("/api/auth/logout")
        for _ in range(5):
            response = self.client.post("/api/auth/login", json={
                "email": "rate-limit@example.com", "password": "wrong password",
            })
            self.assertEqual(response.status_code, 401)
        limited = self.client.post("/api/auth/login", json={
            "email": "rate-limit@example.com", "password": "correct horse battery",
        })
        self.assertEqual(limited.status_code, 429)
        self.assertIn("Retry-After", limited.headers)

    def test_model_failure_does_not_hide_calculation_endpoints(self):
        self.sign_in()
        response = self.client.post("/api/recommendations/explain", json={
            "mode": "prepaid", "case": read_fixture("prepaid-request.example.json"),
        })
        self.assertEqual(response.status_code, 503)
        ordinary_analysis = self.client.post("/api/prepaid/analyze", json=read_fixture("prepaid-request.example.json"))
        self.assertEqual(ordinary_analysis.status_code, 200)


if __name__ == "__main__":
    unittest.main()

