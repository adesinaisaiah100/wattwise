"""Minimal client for the standalone llama.cpp OpenAI-compatible server."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ModelUnavailable(RuntimeError):
    pass


def generate_routine_proposal(*, base_url: str, model: str, timeout: float,
                              mode: str, goal: dict, appliances: list[dict],
                              analysis: dict, feedback: dict | None = None) -> dict:
    """Ask the local model for a bounded, structured household schedule proposal."""
    household = [{
        "id": item["id"], "name": item["label"], "quantity": item["quantity"],
        "essential": item["essential"], "category": item["category"],
        "energy_input": item["energy_input"], "routine": item["routine"],
    } for item in appliances]
    context = {"service_type": mode, "goal": goal, "calculated_baseline": analysis,
               "appliances": household, "feedback_on_previous_draft": feedback}
    system = (
        "You are WattWise's household routine planner. Create a safe, practical appliance schedule "
        "that aims to meet the user's stated electricity goal. Never change an essential appliance. "
        "Never increase appliance use above its current routine. Include every supplied appliance ID "
        "exactly once. For power_and_schedule items, return hours_per_use_day from 0 to the current "
        "hours and uses_per_week from 0 to the current days. For known_daily_energy items, keep "
        "hours_per_use_day unchanged and only adjust uses_per_week. Keep changes realistic and explain "
        "them kindly. Return only valid JSON with this schema: {\"title\": string, \"summary\": string, "
        "\"schedule\": [{\"appliance_id\": string, \"hours_per_use_day\": number, "
        "\"uses_per_week\": number, \"reason\": string}], \"tips\": [string]}. "
        "Do not include calculated kWh; WattWise calculates and verifies all numbers."
        " If feedback says the goal was missed, create a meaningfully lower flexible-use schedule "
        "and try again while protecting every essential appliance."
    )
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": "Create the routine proposal for this household. /no_think\n" + json.dumps(context)},
        ],
        "temperature": 0.15,
        "max_tokens": 900,
        "response_format": {"type": "json_object"},
        "reasoning_effort": "none",
    }).encode("utf-8")
    request = Request(base_url.rstrip("/") + "/chat/completions", data=body,
                      headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read(128000).decode("utf-8"))
        content = payload["choices"][0]["message"]["content"]
        proposal = json.loads(content)
    except (TimeoutError, URLError, HTTPError, OSError, json.JSONDecodeError,
            KeyError, IndexError, TypeError) as exc:
        raise ModelUnavailable("The local model could not create a readable routine plan.") from exc
    if (not isinstance(proposal, dict) or not isinstance(proposal.get("title"), str)
            or not isinstance(proposal.get("summary"), str)
            or not isinstance(proposal.get("schedule"), list)):
        raise ModelUnavailable("The local model returned a routine plan in an unexpected format.")
    return proposal


def stream_explanation(*, base_url: str, model: str, timeout: float, mode: str,
                       result: dict, selected_routine_id: str | None = None):
    """Yield plain-language explanation text as llama.cpp streams it."""
    approved_options = result.get("routine_options", [])
    selected = next((option for option in approved_options if option["id"] == selected_routine_id), None)
    context = {
        "mode": mode,
        "analysis": {key: result.get(key) for key in (
            "target_days", "available_units_kwh", "daily_budget_kwh",
            "estimated_daily_consumption_kwh", "estimated_target_consumption_kwh",
            "projected_duration_days", "units_after_target_kwh", "target_met",
            "estimated_household_kwh", "estimated_daily_kwh", "billed_consumption",
            "comparisons", "assumptions", "warnings",
        ) if key in result},
        "selected_routine": selected,
        "routine_options": [{key: option.get(key) for key in (
            "id", "label", "changes", "estimated_daily_kwh", "estimated_period_kwh",
            "projected_duration_days", "units_after_target_kwh", "target_met",
        ) if key in option} for option in approved_options],
    }
    system = (
        "Explain these WattWise calculations to a Nigerian household in plain, friendly language. "
        "Use only the supplied facts. Do not calculate or change numbers, invent a tariff, claim fraud, "
        "or recommend reducing an essential appliance. Mention uncertainty where relevant. "
        "Write two or three short sentences as plain text, with no heading or list."
    )
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": "Explain these already-calculated results. /no_think\n" + json.dumps(context)},
        ],
        "temperature": 0.2,
        "max_tokens": 180,
        "stream": True,
        "reasoning_effort": "none",
    }).encode("utf-8")
    request = Request(base_url.rstrip("/") + "/chat/completions", data=body,
                      headers={"Content-Type": "application/json", "Accept": "text/event-stream"}, method="POST")
    total = 0
    try:
        with urlopen(request, timeout=timeout) as response:
            while True:
                line = response.readline(65536)
                if not line:
                    break
                line = line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    payload = json.loads(data)
                    text = payload["choices"][0].get("delta", {}).get("content", "")
                except (KeyError, IndexError, TypeError, json.JSONDecodeError):
                    continue
                if not isinstance(text, str) or not text:
                    continue
                total += len(text)
                if total > 2200:
                    raise ModelUnavailable("The explanation was longer than expected. Your estimate is still available.")
                yield text
    except ModelUnavailable:
        raise
    except (TimeoutError, URLError, HTTPError, OSError) as exc:
        raise ModelUnavailable("The explanation service did not respond in time. Your estimate is still available.") from exc


def explain(*, base_url: str, model: str, timeout: float, mode: str,
            result: dict, selected_routine_id: str | None = None) -> dict:
    approved_options = result.get("routine_options", [])
    selected = next((option for option in approved_options if option["id"] == selected_routine_id), None)
    context = {
        "mode": mode,
        "analysis": {key: result.get(key) for key in (
            "target_days", "available_units_kwh", "daily_budget_kwh",
            "estimated_daily_consumption_kwh", "estimated_target_consumption_kwh",
            "projected_duration_days", "units_after_target_kwh", "target_met",
            "estimated_household_kwh", "estimated_daily_kwh", "billed_consumption",
            "comparisons", "assumptions", "warnings",
        ) if key in result},
        "selected_routine": selected,
        "routine_options": [{key: option.get(key) for key in (
            "id", "label", "changes", "estimated_daily_kwh", "estimated_period_kwh",
            "projected_duration_days", "units_after_target_kwh", "target_met",
        ) if key in option} for option in approved_options],
    }
    system = (
        "You explain WattWise results to a Nigerian household in simple, respectful language. "
        "Use only the supplied facts. Do not calculate, change numbers, invent tariffs, claim fraud, "
        "or recommend changing an essential appliance. Explain uncertainty. Return JSON only with "
        "summary (string), key_points (array of strings), recommended_routine_ids (array of supplied IDs), "
        "cautions (array of strings), and next_steps (array of strings). Keep it concise."
    )
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": "Explain these calculated WattWise results. /no_think\n" + json.dumps(context)},
        ],
        "temperature": 0.2,
        "max_tokens": 350,
        "response_format": {"type": "json_object"},
        "reasoning_effort": "none",
    }).encode("utf-8")
    request = Request(base_url.rstrip("/") + "/chat/completions", data=body,
                      headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read(128000).decode("utf-8"))
    except (TimeoutError, URLError, HTTPError, OSError, json.JSONDecodeError) as exc:
        raise ModelUnavailable("The local Qwen server is unavailable or did not respond in time.") from exc
    try:
        content = payload["choices"][0]["message"]["content"]
        parsed = json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise ModelUnavailable("The local model returned an unreadable explanation.") from exc
    if not isinstance(parsed, dict) or not isinstance(parsed.get("summary"), str):
        raise ModelUnavailable("The local model returned an invalid explanation format.")
    fields = {"summary": parsed["summary"][:700]}
    for key in ("key_points", "cautions", "next_steps"):
        value = parsed.get(key, [])
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            value = []
        fields[key] = [item[:240] for item in value[:5]]
    allowed = {option["id"] for option in approved_options}
    selected_ids = parsed.get("recommended_routine_ids", [])
    if not isinstance(selected_ids, list):
        selected_ids = []
    fields["recommended_routine_ids"] = [item for item in selected_ids if item in allowed][:3]
    return fields

