"""HTTP endpoints for the browser and local model explanation."""

from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import urlopen

from flask import Blueprint, Response, current_app, g, jsonify, request, stream_with_context
from werkzeug.exceptions import BadRequest

from ai.adapter import ModelUnavailable, explain, generate_routine_proposal, stream_explanation
from auth.security import require_auth, require_mode
from core.consumption import estimate_household
from core.validation import InputError, number, object_payload, validate_appliances
from services.analysis import analyze_case, prepare_postpaid, prepare_prepaid
from services.planning import create_verified_plan

api = Blueprint("api", __name__)


class MalformedJson(Exception):
    pass


def success(data: dict, warnings: list | None = None):
    return jsonify({"success": True, "data": data, "warnings": warnings or []})


def error_response(error: InputError, status: int = 422):
    return jsonify({"success": False, "error": {
        "code": "VALIDATION_ERROR", "message": str(error), "details": error.details,
    }}), status


def request_object() -> dict:
    if not request.is_json:
        raise MalformedJson
    try:
        payload = request.get_json()
    except BadRequest:
        raise MalformedJson from None
    return object_payload(payload)


def malformed_json_response():
    return jsonify({"success": False, "error": {
        "code": "MALFORMED_JSON",
        "message": "Send a valid JSON request body.",
        "details": [],
    }}), 400


@api.errorhandler(MalformedJson)
def handle_malformed_json(_error):
    return malformed_json_response()


@api.errorhandler(InputError)
def handle_input_error(error):
    return error_response(error)


@api.get("/health")
def health():
    base_url = current_app.config["LLAMA_BASE_URL"].rstrip("/")
    server_url = base_url[:-3] if base_url.endswith("/v1") else base_url
    model_state = "not_loaded"
    try:
        with urlopen(server_url + "/health", timeout=0.35):
            model_state = "ready"
    except (URLError, TimeoutError, OSError):
        pass
    return success({"app": "ready", "calculation_engine": "ready", "model": model_state})


@api.post("/consumption/estimate")
@require_auth
def consumption_estimate():
    body = request_object()
    days = number(body.get("period_days"), "period_days", minimum=1, maximum=366)
    appliances = validate_appliances(body.get("appliances"))
    return success(estimate_household(appliances, days))


@api.post("/prepaid/analyze")
@require_auth
@require_mode("prepaid")
def prepaid_analyze():
    body = request_object()
    _, result = prepare_prepaid(body)
    return success(result, result.get("warnings"))


@api.post("/postpaid/analyze")
@require_auth
@require_mode("postpaid")
def postpaid_analyze():
    body = request_object()
    _, result = prepare_postpaid(body)
    return success(result, result.get("warnings"))


@api.post("/recommendations/explain")
@require_auth
def recommendations_explain():
    body = request_object()
    mode = body.get("mode")
    mode_error = _requested_mode_error(mode)
    if mode_error:
        return mode_error
    case = object_payload(body.get("case"))
    normalized, result = analyze_case(mode, case)
    try:
        explanation = explain(
            base_url=current_app.config["LLAMA_BASE_URL"],
            model=current_app.config["LLAMA_MODEL"],
            timeout=current_app.config["LLAMA_TIMEOUT_SECONDS"],
            mode=mode,
            result=result,
            selected_routine_id=body.get("selected_routine_id"),
        )
    except ModelUnavailable as exc:
        return jsonify({"success": False, "error": {
            "code": "MODEL_UNAVAILABLE", "message": str(exc), "details": [],
        }}), 503
    return success({"mode": mode, "explanation": explanation, "analysis": result})


@api.post("/recommendations/plan")
@require_auth
def recommendations_plan():
    body = request_object()
    mode = body.get("mode")
    mode_error = _requested_mode_error(mode)
    if mode_error:
        return mode_error
    case = object_payload(body.get("case"))
    normalized, result, reduction, goal = _prepare_ai_plan(mode, case)
    try:
        plan = None
        for event in _plan_generation_events(mode, normalized, result, reduction, goal):
            if event["type"] == "plan":
                plan = event["plan"]
    except ModelUnavailable as exc:
        return jsonify({"success": False, "error": {
            "code": "MODEL_UNAVAILABLE", "message": str(exc), "details": [],
        }}), 503
    except InputError as exc:
        return jsonify({"success": False, "error": {
            "code": "AI_PLAN_INVALID", "message": "The local model returned a schedule WattWise could not verify. Please try again.",
            "details": exc.details,
        }}), 502
    return success({"plan": plan})


@api.post("/recommendations/plan/stream")
@require_auth
def recommendations_plan_stream():
    body = request_object()
    mode = body.get("mode")
    mode_error = _requested_mode_error(mode)
    if mode_error:
        return mode_error
    case = object_payload(body.get("case"))
    normalized, result, reduction, goal = _prepare_ai_plan(mode, case)

    def events():
        try:
            for event in _plan_generation_events(mode, normalized, result, reduction, goal):
                yield "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"
        except ModelUnavailable as exc:
            yield "data: " + json.dumps({"type": "error", "code": "MODEL_UNAVAILABLE", "message": str(exc)}) + "\n\n"
        except InputError as exc:
            yield "data: " + json.dumps({"type": "error", "code": "AI_PLAN_INVALID", "message": "The local model returned a schedule WattWise could not verify. Please try again."}) + "\n\n"

    return Response(stream_with_context(events()), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
    })


def _prepare_ai_plan(mode: str, case: dict):
    normalized, result = analyze_case(mode, case)
    reduction = None
    if mode == "prepaid":
        goal = {
            "type": "make_prepaid_units_last", "target_days": result["target_days"],
            "available_units_kwh": result["available_units_kwh"],
            "daily_energy_budget_kwh": result["daily_budget_kwh"],
        }
    else:
        reduction = number(case.get("target_reduction_percent"), "target_reduction_percent", minimum=5, maximum=80)
        result["tariff_rate_ngn_per_kwh"] = normalized["tariff"]["rate_ngn_per_kwh"]
        goal = {
            "type": "reduce_estimated_household_use", "reduction_percent": reduction,
            "billing_period_days": result["billing_period_days"],
        }
    return normalized, result, reduction, goal


def _plan_generation_events(mode: str, normalized: dict, result: dict,
                            reduction: float | None, goal: dict):
    feedback = None
    proposal = None
    plan = None
    max_model_rounds = 3
    for round_number in range(1, max_model_rounds + 1):
        yield {"type": "progress", "round": round_number, "message": f"Qwen is drafting routine {round_number} of {max_model_rounds}."}
        proposal = generate_routine_proposal(
            base_url=current_app.config["LLAMA_BASE_URL"],
            model=current_app.config["LLAMA_MODEL"],
            timeout=current_app.config["LLAMA_TIMEOUT_SECONDS"],
            mode=mode,
            goal=goal,
            appliances=normalized["appliances"],
            analysis=result,
            feedback=feedback,
        )
        plan = create_verified_plan(
            mode=mode,
            appliances=normalized["appliances"],
            analysis=result,
            proposal=proposal,
            target_reduction_percent=reduction,
            fit_to_goal=False,
            proposal_rounds=round_number,
        )
        if plan["goal"]["achieved"]:
            break
        feedback = {
            "target_period_kwh": plan["goal"]["target_period_kwh"],
            "verified_period_kwh": plan["goal"]["estimated_period_kwh"],
            "shortfall_kwh": max(0, plan["goal"]["estimated_period_kwh"] - plan["goal"]["target_period_kwh"]),
            "essential_appliances_unchanged": True,
            "previous_schedule": [{
                "appliance_id": row["appliance_id"],
                "hours_per_use_day": row["hours_per_use_day"],
                "uses_per_week": row["uses_per_week"],
            } for row in plan["schedule"]],
        }
        yield {"type": "progress", "round": round_number, "message": "That draft missed your goal. Qwen is revising flexible appliance routines; essential items stay unchanged."}
    if plan and not plan["goal"]["achieved"]:
        plan = create_verified_plan(
            mode=mode,
            appliances=normalized["appliances"],
            analysis=result,
            proposal=proposal,
            target_reduction_percent=reduction,
            fit_to_goal=True,
            proposal_rounds=max_model_rounds,
        )
    yield {"type": "plan", "plan": plan}


@api.post("/recommendations/explain/stream")
@require_auth
def recommendations_explain_stream():
    body = request_object()
    mode = body.get("mode")
    mode_error = _requested_mode_error(mode)
    if mode_error:
        return mode_error
    case = object_payload(body.get("case"))
    _, result = analyze_case(mode, case)

    def events():
        yield "data: {\"type\":\"status\",\"message\":\"Preparing your explanation\"}\n\n"
        try:
            for text in stream_explanation(
                base_url=current_app.config["LLAMA_BASE_URL"],
                model=current_app.config["LLAMA_MODEL"],
                timeout=current_app.config["LLAMA_TIMEOUT_SECONDS"],
                mode=mode,
                result=result,
                selected_routine_id=body.get("selected_routine_id"),
            ):
                yield "data: " + json.dumps({"type": "token", "text": text}, ensure_ascii=False) + "\n\n"
        except ModelUnavailable as exc:
            yield "data: " + json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False) + "\n\n"
            return
        yield "data: {\"type\":\"done\"}\n\n"

    return Response(stream_with_context(events()), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
    })


def _requested_mode_error(mode: str | None):
    selected = g.current_user.get("preferred_mode")
    if selected is None:
        return jsonify({"success": False, "error": {
            "code": "HOUSEHOLD_SETUP_REQUIRED",
            "message": "Choose prepaid or postpaid to finish setting up your household.",
            "details": [],
        }}), 409
    if mode != selected:
        return jsonify({"success": False, "error": {
            "code": "SERVICE_TYPE_MISMATCH",
            "message": "This account is set up for a different electricity service type.",
            "details": [],
        }}), 403
    return None

