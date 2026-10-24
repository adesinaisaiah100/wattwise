(() => {
  const form = document.querySelector("#analysis-form");
  if (!form) return;
  const mode = form.dataset.mode;
  const list = form.querySelector("[data-appliance-list]");
  const template = form.querySelector("[data-appliance-template]");
  const results = document.querySelector("#results");
  let lastRequest = null;
  let isSignedIn = false;

  const numeric = (value) => value === "" || value == null ? null : Number(value);
  const valueOf = (card, name) => card.querySelector(`[data-field="${name}"]`)?.value ?? "";

  function addAppliance(saved = null) {
    const fragment = template.content.cloneNode(true);
    const card = fragment.querySelector("[data-appliance-card]");
    const id = globalThis.crypto?.randomUUID?.() || `appliance-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    card.querySelector('[data-field="id"]').value = id;
    list.append(fragment);
    const newCard = list.lastElementChild;
    if (saved) restoreAppliance(newCard, saved);
    else refreshCard(newCard);
  }

  function refreshCard(card, applyDefaults = false) {
    if (!card) return;
    const selector = card.querySelector('[data-field="appliance_type"]');
    const choice = selector?.selectedOptions[0];
    const selected = Boolean(choice?.value);
    const measured = Boolean(choice?.dataset.daily);
    const custom = choice?.value === "other";
    const powerLabel = card.querySelector("[data-power-field]");
    const dailyLabel = card.querySelector("[data-daily-field]");
    const hoursLabel = card.querySelector("[data-hours-field]");
    const routineBox = card.querySelector("[data-routine-box]");
    const customLabel = card.querySelector("[data-custom-label]");
    const power = card.querySelector('[data-field="power_watts"]');
    const daily = card.querySelector('[data-field="kwh_per_use_day"]');
    const hours = card.querySelector('[data-field="hours_per_use_day"]');
    const title = card.querySelector("[data-card-title]");
    routineBox.hidden = !selected;
    customLabel.hidden = !custom;
    powerLabel.hidden = measured;
    dailyLabel.hidden = !measured;
    hoursLabel.hidden = measured;
    power.required = selected && !measured;
    daily.required = selected && measured;
    hours.required = selected && !measured;
    card.querySelector('[data-field="label"]').required = custom;
    if (!selected) return;
    card.querySelector('[data-field="category"]').value = choice.dataset.category || "other";
    title.textContent = choice.dataset.label || "Appliance";
    const label = card.querySelector('[data-field="label"]');
    label.value = choice.dataset.label || "Other appliance";
    if (applyDefaults) {
      card.querySelector('[data-field="quantity"]').value = 1;
      card.querySelector('[data-field="essential"]').value = choice.dataset.essential === "true" ? "true" : "false";
      card.querySelector('[data-field="uses_per_week"]').value = choice.dataset.days || 7;
      card.querySelector('[data-field="hours_per_use_day"]').value = choice.dataset.hours || 2;
      power.value = choice.dataset.watts || "";
      daily.value = choice.dataset.daily || "";
      card.querySelector('[data-field="source"]').value = "catalog_estimate";
      card.dataset.energyMethod = "";
    }
    card.querySelector("[data-estimate-summary]").textContent = measured
      ? `Typical estimate: ${daily.value || choice.dataset.daily} kWh on a day you use it`
      : `Typical estimate: ${power.value || choice.dataset.watts} watts per appliance`;
  }

  function restoreAppliance(card, appliance) {
    const selector = card.querySelector('[data-field="appliance_type"]');
    const known = [...selector.options].some((option) => option.value === appliance.type);
    selector.value = known ? appliance.type : "other";
    refreshCard(card, !appliance.energy_input);
    card.querySelector('[data-field="label"]').value = appliance.label || "Other appliance";
    card.querySelector('[data-field="category"]').value = appliance.category || "other";
    card.querySelector('[data-field="quantity"]').value = appliance.quantity || 1;
    card.querySelector('[data-field="essential"]').value = String(Boolean(appliance.essential));
    card.querySelector('[data-field="uses_per_week"]').value = appliance.routine?.uses_per_week ?? 7;
    const measured = appliance.energy_input?.method === "known_daily_energy";
    card.querySelector('[data-field="power_watts"]').value = appliance.energy_input?.power_watts ?? "";
    card.querySelector('[data-field="kwh_per_use_day"]').value = appliance.energy_input?.kwh_per_use_day ?? "";
    card.querySelector('[data-field="hours_per_use_day"]').value = appliance.routine?.hours_per_use_day ?? 2;
    card.querySelector('[data-field="source"]').value = appliance.energy_input?.source || "user_entered";
    card.dataset.energyMethod = appliance.energy_input?.method || "";
    refreshRestoredCard(card, measured);
  }

  function refreshRestoredCard(card, measured) {
    const selector = card.querySelector('[data-field="appliance_type"]');
    const choice = selector.selectedOptions[0];
    const dailyMode = measured || Boolean(choice?.dataset.daily);
    card.querySelector("[data-routine-box]").hidden = false;
    card.querySelector("[data-custom-label]").hidden = choice?.value !== "other";
    card.querySelector("[data-power-field]").hidden = dailyMode;
    card.querySelector("[data-daily-field]").hidden = !dailyMode;
    card.querySelector("[data-hours-field]").hidden = dailyMode;
    card.querySelector('[data-field="power_watts"]').required = !dailyMode;
    card.querySelector('[data-field="kwh_per_use_day"]').required = dailyMode;
    card.querySelector('[data-field="hours_per_use_day"]').required = !dailyMode;
    card.querySelector('[data-card-title]').textContent = card.querySelector('[data-field="label"]').value;
    card.querySelector("[data-estimate-summary]").textContent = dailyMode
      ? `Saved estimate: ${card.querySelector('[data-field="kwh_per_use_day"]').value} kWh on a day you use it`
      : `Saved estimate: ${card.querySelector('[data-field="power_watts"]').value} watts per appliance`;
  }

  function collectAppliances() {
    return [...list.querySelectorAll("[data-appliance-card]")].map((card) => {
      const choice = card.querySelector('[data-field="appliance_type"]').selectedOptions[0];
      const method = card.dataset.energyMethod || (choice?.dataset.daily ? "known_daily_energy" : "power_and_schedule");
      const energy = {
        method,
        source: valueOf(card, "source"),
        ...(method === "power_and_schedule"
          ? { power_watts: numeric(valueOf(card, "power_watts")), usage_factor: 1.0 }
          : { kwh_per_use_day: numeric(valueOf(card, "kwh_per_use_day")) }),
      };
      return {
        id: valueOf(card, "id"),
        type: choice.value === "other" ? "custom" : choice.value,
        label: (choice.value === "other" ? valueOf(card, "label") : choice.dataset.label).trim(),
        category: valueOf(card, "category"),
        quantity: numeric(valueOf(card, "quantity")),
        essential: valueOf(card, "essential") === "true",
        energy_input: energy,
        routine: {
          hours_per_use_day: method === "power_and_schedule" ? numeric(valueOf(card, "hours_per_use_day")) : null,
          uses_per_week: numeric(valueOf(card, "uses_per_week")),
          preferred_time: valueOf(card, "preferred_time") || null,
        },
      };
    });
  }

  function collectRequest() {
    const appliances = collectAppliances();
    if (mode === "prepaid") {
      const request = {
        target_days: numeric(form.elements.target_days.value),
        available_units_kwh: numeric(form.elements.available_units_kwh.value),
        appliances,
      };
      const receipt = {
        amount_paid_ngn: numeric(form.elements.receipt_amount.value),
        units_credited_kwh: numeric(form.elements.receipt_units.value),
        rate_ngn_per_kwh: numeric(form.elements.receipt_rate.value),
      };
      if (Object.values(receipt).some((value) => value !== null)) request.topup_receipt = receipt;
      return request;
    }
    return {
      billing_period: { days: numeric(form.elements.period_days.value) },
      billed_consumption: {
        units_kwh: numeric(form.elements.billed_kwh.value),
        previous_reading_kwh: numeric(form.elements.previous_reading.value),
        present_reading_kwh: numeric(form.elements.present_reading.value),
        multiplier: numeric(form.elements.multiplier.value) ?? 1,
        reading_type: form.elements.reading_type.value,
      },
      tariff: { rate_ngn_per_kwh: numeric(form.elements.tariff.value) },
      target_reduction_percent: numeric(form.elements.target_reduction_percent.value),
      bill: {
        energy_charge_ngn: numeric(form.elements.energy_charge.value),
        total_amount_ngn: numeric(form.elements.total_amount.value),
        other_charges_ngn: numeric(form.elements.other_charges.value),
      },
      appliances,
    };
  }

  function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function numberText(value, digits = 2) {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) return "Not available";
    return Number(value).toLocaleString("en-NG", { maximumFractionDigits: digits });
  }

  function naira(value) {
    return value === null || value === undefined ? "Not available" : `₦${numberText(value)}`;
  }

  function renderError(message, details = []) {
    results.hidden = false;
    results.replaceChildren();
    const box = node("div", "notice notice-error");
    box.append(node("strong", "", message));
    for (const detail of details) {
      if (detail?.field) box.append(node("p", "error-detail", `${detail.field}: ${detail.issue || "check this value"}`));
    }
    results.append(box);
  }

  function renderResults(data) {
    results.hidden = false;
    results.replaceChildren();
    results.append(node("p", "eyebrow", "YOUR ESTIMATE"));
    results.append(node("h2", "results-heading", mode === "prepaid" ? "Your unit plan" : "Your bill analysis"));

    const metrics = node("div", "metric-grid");
    if (mode === "prepaid") {
      metrics.append(metric("Daily energy budget", `${numberText(data.daily_budget_kwh)} kWh`));
      metrics.append(metric("Estimated daily use", `${numberText(data.estimated_daily_consumption_kwh)} kWh`));
      metrics.append(metric("Estimated duration", data.projected_duration_days == null ? "No estimated use" : `${numberText(data.projected_duration_days)} days`));
      metrics.append(metric(data.units_after_target_kwh >= 0 ? "Estimated units left" : "Estimated shortfall", `${numberText(Math.abs(data.units_after_target_kwh))} kWh`));
      results.append(metrics);
      results.append(node("p", data.target_met ? "status-line status-good" : "status-line status-warn",
        data.target_met ? "Your current routine is estimated to fit within this target." : "Your current routine is estimated to use more than the available units."));
      if (data.topup_receipt) {
        const receipt = data.topup_receipt;
        const section = node("div", "result-section receipt-context");
        section.append(node("h3", "", "Recent top-up receipt context"));
        const details = [];
        if (receipt.amount_paid_ngn != null) details.push(`Amount paid: ${naira(receipt.amount_paid_ngn)}`);
        if (receipt.units_credited_kwh != null) details.push(`Units credited: ${numberText(receipt.units_credited_kwh)} kWh`);
        if (receipt.rate_ngn_per_kwh != null) details.push(`Tariff shown: ${naira(receipt.rate_ngn_per_kwh)} per kWh`);
        details.forEach((detail) => section.append(node("p", "", detail)));
        section.append(node("p", "helper", "Receipt values are shown for reference. The plan uses the current meter balance entered above."));
        results.append(section);
      }
    } else {
      metrics.append(metric("Estimated household use", `${numberText(data.estimated_household_kwh)} kWh`));
      metrics.append(metric("Billed consumption", data.billed_consumption.units_kwh == null ? "Not supplied" : `${numberText(data.billed_consumption.units_kwh)} kWh`));
      metrics.append(metric("Estimated energy charge", naira(data.estimated_household_energy_charge_ngn)));
      metrics.append(metric("Total amount due", naira(data.total_amount_due_ngn)));
      results.append(metrics);
      const note = data.billed_consumption.source === "readings_derived" ? "Billed kWh was derived from the readings you entered." : "Billed kWh is shown only when supplied or derived from usable readings.";
      results.append(node("p", "helper", note));
    }

    if (data.appliance_breakdown?.length) {
      const section = node("div", "result-section");
      section.append(node("h3", "", "Estimated use by appliance"));
      const listEl = node("ul", "breakdown-list");
      data.appliance_breakdown.forEach((item) => listEl.append(node("li", "breakdown-row", `${item.label}: ${numberText(item.period_kwh)} kWh over the period`)));
      section.append(listEl);
      results.append(section);
    }

    if (data.comparisons?.length) {
      const section = node("div", "result-section");
      section.append(node("h3", "", "Bill checks"));
      data.comparisons.forEach((item) => {
        const label = item.kind === "estimated_minus_billed_kwh"
          ? `Household estimate minus billed units: ${numberText(item.difference_kwh)} kWh`
          : `Expected energy charge minus supplied energy charge: ${naira(item.difference_ngn)}`;
        section.append(node("p", "comparison-row", label));
      });
      results.append(section);
    }

    renderAiPlanner();

    [...(data.assumptions || []), ...(data.warnings || [])].forEach((text) => results.append(node("p", "notice notice-neutral", text)));

    const actions = node("div", "result-actions");
    const saveHistory = node("button", "button button-outline", isSignedIn ? "Save this analysis" : "Sign in to save this analysis");
    saveHistory.type = "button";
    saveHistory.addEventListener("click", (event) => saveAccountData(
      event.currentTarget, "/api/account/history", { mode, case: lastRequest },
      "Analysis saved to your local account.",
    ));
    actions.append(saveHistory);
    const saveAppliances = node("button", "button button-outline", isSignedIn ? "Save appliance setup" : "Sign in to save appliance setup");
    saveAppliances.type = "button";
    saveAppliances.addEventListener("click", (event) => saveAccountData(
      event.currentTarget, "/api/account/appliances", { appliances: lastRequest.appliances },
      "Appliance setup saved to your local account.", "PUT",
    ));
    actions.append(saveAppliances);
    const explainButton = node("button", "button button-secondary", "Explain my results");
    explainButton.type = "button";
    explainButton.addEventListener("click", requestExplanation);
    actions.append(explainButton);
    actions.append(node("span", "helper", "Optional. Your estimate works without this."));
    results.append(actions);
    const explanation = node("div", "explanation-box");
    explanation.dataset.explanation = "true";
    explanation.hidden = true;
    results.append(explanation);
  }

  async function saveAccountData(button, endpoint, body, successText, method = "POST") {
    if (!isSignedIn) { window.location.assign("/login"); return; }
    button.disabled = true;
    const oldText = button.textContent;
    button.textContent = "Saving…";
    try {
      const response = await fetch(endpoint, {
        method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
      });
      const payload = await response.json();
      if (!response.ok || !payload.success) throw new Error(payload.error?.message || "Could not save this data.");
      button.textContent = "Saved";
      const note = node("p", "save-feedback", successText);
      button.closest(".result-actions").append(note);
    } catch (error) {
      button.textContent = oldText;
      renderError(error.message);
    } finally {
      button.disabled = false;
    }
  }

  function metric(label, value) {
    const card = node("div", "metric-card");
    card.append(node("span", "metric-label", label));
    card.append(node("strong", "metric-value", value));
    return card;
  }

  function applyAiPlan(plan) {
    for (const row of plan.schedule) {
      const card = [...list.querySelectorAll("[data-appliance-card]")]
        .find((item) => valueOf(item, "id") === row.appliance_id);
      if (!card) continue;
      const hours = card.querySelector('[data-field="hours_per_use_day"]');
      const days = card.querySelector('[data-field="uses_per_week"]');
      if (hours && row.hours_per_use_day != null) hours.value = row.hours_per_use_day;
      if (days && row.uses_per_week != null) days.value = row.uses_per_week;
    }
    form.scrollIntoView({ behavior: "smooth", block: "start" });
    form.requestSubmit();
  }

  function renderAiPlanner() {
    const section = node("section", "result-section ai-planner");
    section.append(node("p", "step-kicker", "WATTWISE AI PLANNER"));
    section.append(node("h3", "", "Build a routine around your goal"));
    section.append(node("p", "helper", mode === "prepaid"
      ? "The AI will draft an appliance schedule for the number of days you want your current meter units to last. WattWise checks the energy totals before showing it."
      : "The AI will draft an appliance schedule toward your household-use reduction goal. WattWise checks the energy totals before showing it."));
    const button = node("button", "button button-primary", "Generate my AI routine plan");
    button.type = "button";
    const status = node("p", "plan-status helper");
    status.setAttribute("role", "status");
    const output = node("div", "ai-plan-output");
    output.hidden = true;
    button.addEventListener("click", async () => {
      button.disabled = true;
      button.textContent = "Building your routine…";
      status.textContent = "Qwen is drafting a schedule. WattWise will calculate and verify every appliance before showing it.";
      output.hidden = true;
      output.replaceChildren();
      try {
        const response = await fetch("/api/recommendations/plan/stream", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mode, case: lastRequest }),
        });
        if (!response.ok || !response.body) {
          let message = "The AI plan could not be created.";
          try { message = (await response.json()).error?.message || message; } catch (_error) { /* Keep fallback. */ }
          throw new Error(message);
        }
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let pending = "";
        let plan = null;
        const consumeEvents = (chunk) => {
          for (const eventText of chunk.split("\n\n")) {
            const line = eventText.split("\n").find((item) => item.startsWith("data: "));
            if (!line) continue;
            const data = JSON.parse(line.slice(6));
            if (data.type === "progress") status.textContent = data.message;
            if (data.type === "error") throw new Error(data.message || "The AI plan could not be created.");
            if (data.type === "plan") plan = data.plan;
          }
        };
        while (true) {
          const { value, done } = await reader.read();
          pending += decoder.decode(value || new Uint8Array(), { stream: !done });
          const events = pending.split("\n\n");
          pending = events.pop() || "";
          consumeEvents(events.join("\n\n"));
          if (done) {
            if (pending.trim()) consumeEvents(`${pending}\n\n`);
            break;
          }
        }
        if (!plan) throw new Error("The model finished without returning a verified plan.");
        status.textContent = "Plan ready. Review the schedule and apply it if it fits your household.";
        renderAiPlan(output, plan);
        output.hidden = false;
      } catch (error) {
        status.textContent = error.message;
      } finally {
        button.disabled = false;
        button.textContent = "Generate my AI routine plan";
      }
    });
    section.append(button, status, output);
    results.append(section);
  }

  function renderAiPlan(container, plan) {
    container.replaceChildren();
    const head = node("div", "ai-plan-heading");
    head.append(node("p", "step-kicker", "AI GENERATED | CALCULATION CHECKED"));
    head.append(node("h4", "", plan.title));
    head.append(node("p", "ai-plan-summary", plan.summary));
    container.append(head);

    const goal = node("div", plan.goal.achieved ? "plan-goal plan-goal-met" : "plan-goal plan-goal-nearest");
    goal.append(node("strong", "", plan.goal.achieved ? "Your goal is within reach with this routine." : "This is the closest safe routine we could calculate."));
    goal.append(node("span", "", `${plan.goal.label}. Planned use: ${numberText(plan.goal.estimated_period_kwh)} of ${numberText(plan.goal.target_period_kwh)} kWh over ${numberText(plan.goal.period_days)} days.`));
    container.append(goal);

    const metrics = node("div", "ai-plan-metrics");
    metrics.append(metric("Your current average", `${numberText(plan.goal.baseline_daily_kwh)} kWh/day`));
    metrics.append(metric("Estimated use each day", `${numberText(plan.goal.estimated_daily_kwh)} kWh`));
    metrics.append(metric(`Estimated use over ${numberText(plan.goal.period_days)} days`, `${numberText(plan.goal.estimated_period_kwh)} kWh`));
    metrics.append(metric("Estimated energy saved", `${numberText(plan.goal.saved_period_kwh)} kWh`));
    if (plan.estimated_energy_charge_ngn != null) {
      metrics.append(metric("Estimated energy charge", naira(plan.estimated_energy_charge_ngn)));
      metrics.append(metric("Estimated charge reduction", naira(plan.estimated_charge_savings_ngn)));
    }
    container.append(metrics);

    const chart = node("div", "plan-chart");
    chart.setAttribute("role", "img");
    chart.setAttribute("aria-label", "Comparison chart showing usual and suggested daily energy use by appliance");
    chart.append(node("h5", "", "Daily energy use by appliance"));
    const chartRows = [...plan.schedule].sort((a, b) => b.baseline_daily_kwh - a.baseline_daily_kwh);
    const max = Math.max(...chartRows.map((row) => row.baseline_daily_kwh), 0.01);
    chartRows.forEach((row) => {
      const line = node("div", "plan-chart-row");
      const label = node("span", "plan-chart-label", row.name);
      const pair = node("div", "plan-chart-pair");
      [["Usual", row.baseline_daily_kwh, "usual"], ["Plan", row.daily_kwh, "suggested"]].forEach(([name, value, kind]) => {
        const barLine = node("div", "plan-chart-bar-line");
        const rail = node("span", "plan-chart-rail");
        const bar = node("span", `plan-chart-bar ${kind}`);
        bar.style.width = `${Math.max(value > 0 ? 2 : 0, value / max * 100)}%`;
        rail.append(bar);
        barLine.append(node("span", "plan-chart-kind", name), rail, node("strong", "plan-chart-value", `${numberText(value, 3)} kWh`));
        pair.append(barLine);
      });
      line.append(label, pair);
      chart.append(line);
    });
    container.append(chart);

    const tableWrap = node("div", "routine-table-wrap");
    const table = node("table", "routine-table ai-plan-table");
    table.append(node("caption", "sr-only", "AI-generated appliance schedule"));
    const header = node("tr");
    ["Appliance", "Rating", "Hours per day", "Days per week", "Energy per day", "Why this routine"].forEach((label) => header.append(node("th", "", label)));
    const thead = node("thead"); thead.append(header); table.append(thead);
    const body = node("tbody");
    plan.schedule.forEach((item) => {
      const energy = item.energy_input.method === "known_daily_energy"
        ? `${numberText(item.energy_input.kwh_per_use_day)} kWh on use-days`
        : `${numberText(item.energy_input.power_watts)} W (${item.energy_input.source === "user_entered" ? "your rating" : "typical estimate"})`;
      const row = node("tr", item.essential ? "plan-essential" : "");
      row.append(node("th", "", `${item.quantity} × ${item.name}${item.essential ? " (essential)" : ""}`));
      row.append(node("td", "", energy));
      row.append(node("td", "", item.energy_input.method === "known_daily_energy" ? "—" : `${numberText(item.hours_per_use_day, 1)} hours`));
      row.append(node("td", "", `${numberText(item.uses_per_week, 1)} days`));
      row.append(node("td", "routine-energy", `${numberText(item.daily_kwh, 3)} kWh`));
      row.append(node("td", "plan-reason", item.reason));
      body.append(row);
    });
    table.append(body); tableWrap.append(table); container.append(tableWrap);

    if (plan.tips?.length) {
      const tips = node("div", "ai-plan-tips");
      tips.append(node("h5", "", "AI suggestions to review"));
      plan.tips.forEach((tip) => tips.append(node("p", "", tip)));
      container.append(tips);
    }
    container.append(node("p", "plan-verification", plan.verification));
    const apply = node("button", "button button-outline", "Use this schedule and recalculate");
    apply.type = "button";
    apply.addEventListener("click", () => applyAiPlan(plan));
    container.append(apply);
  }

  async function requestExplanation(event) {
    const button = event.currentTarget;
    const box = results.querySelector("[data-explanation]");
    button.disabled = true;
    button.textContent = "Writing a short explanation…";
    box.hidden = false;
    box.replaceChildren(node("strong", "", "Your results, in plain language"));
    const stream = node("p", "streamed-explanation", "Preparing your explanation…");
    box.append(stream, node("p", "ai-disclaimer", "AI wording can be wrong. The figures calculated above are the source of truth."));
    try {
      const response = await fetch("/api/recommendations/explain/stream", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode, case: lastRequest, selected_routine_id: null }),
      });
      if (!response.ok || !response.body) throw new Error("The explanation could not start. Your calculated result is still available.");
      stream.textContent = "";
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let pending = "";
      let receivedText = false;
      while (true) {
        const { value, done } = await reader.read();
        pending += decoder.decode(value || new Uint8Array(), { stream: !done });
        const events = pending.split("\n\n");
        pending = events.pop() || "";
        for (const eventText of events) {
          const line = eventText.split("\n").find((item) => item.startsWith("data: "));
          if (!line) continue;
          const data = JSON.parse(line.slice(6));
          if (data.type === "token") {
            stream.textContent += data.text;
            receivedText = true;
          }
          if (data.type === "error") throw new Error(data.message);
        }
        if (done) break;
      }
      if (!receivedText) throw new Error("No explanation came back. Your calculated result is still available.");
    } catch (error) {
      stream.textContent = `${error.message} Your calculated result is still available above.`;
    } finally {
      button.disabled = false;
      button.textContent = "Explain my results";
    }
  }

  form.addEventListener("click", (event) => {
    if (event.target.closest("[data-add-appliance]")) addAppliance();
    if (event.target.closest("[data-save-profile]")) saveApplianceProfile(event.target.closest("[data-save-profile]"));
    if (event.target.closest("[data-remove-appliance]")) {
      event.target.closest("[data-appliance-card]").remove();
    }
  });
  form.addEventListener("change", (event) => {
    if (event.target.matches('[data-field="appliance_type"]')) refreshCard(event.target.closest("[data-appliance-card]"), true);
  });
  form.addEventListener("input", (event) => {
    if (event.target.matches('[data-field="label"]')) {
      event.target.closest("[data-appliance-card]").querySelector("[data-card-title]").textContent = event.target.value || "Other appliance";
    }
    if (event.target.matches('[data-field="power_watts"], [data-field="kwh_per_use_day"]')) {
      const card = event.target.closest("[data-appliance-card]");
      card.querySelector('[data-field="source"]').value = "user_entered";
      const estimate = card.querySelector('[data-estimate-summary]');
      estimate.textContent = `Your estimate: ${event.target.value} ${event.target.matches('[data-field="kwh_per_use_day"]') ? "kWh per use-day" : "watts per appliance"}`;
    }
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const request = collectRequest();
    if (!request.appliances.length) {
      renderError("Add at least one appliance so WattWise can estimate your household use.");
      return;
    }
    lastRequest = request;
    const submit = form.querySelector('[type="submit"]');
    submit.disabled = true;
    submit.textContent = "Working out your estimate…";
    results.hidden = false;
    results.replaceChildren(node("p", "helper", "Working out your estimate from the details you entered…"));
    try {
      const response = await fetch(form.dataset.endpoint, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(request),
      });
      const payload = await response.json();
      if (!response.ok || !payload.success) {
        renderError(payload.error?.message || "Please review the information and try again.", payload.error?.details || []);
      } else {
        renderResults(payload.data);
      }
    } catch (_error) {
      renderError("WattWise could not reach its local calculation service. Is the Flask app still running?");
    } finally {
      submit.disabled = false;
      submit.textContent = mode === "prepaid" ? "See my unit plan" : "Compare my bill";
    }
  });

  const profileButton = form.querySelector("[data-save-profile]");
  const signInLink = form.querySelector("[data-save-signin]");
  const profileMessage = form.querySelector("[data-profile-message]");

  async function saveApplianceProfile(button) {
    const cards = [...list.querySelectorAll("[data-appliance-card]")];
    if (!cards.length || cards.some((card) => !valueOf(card, "appliance_type"))) {
      profileMessage.textContent = "Choose at least one appliance before saving your list.";
      profileMessage.hidden = false;
      return;
    }
    const appliances = collectAppliances();
    if (appliances.some((item) => !item.label)) {
      profileMessage.textContent = "Choose an appliance before saving your list.";
      profileMessage.hidden = false;
      return;
    }
    button.disabled = true;
    profileMessage.hidden = true;
    try {
      const response = await fetch("/api/account/appliances", {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ appliances }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.success) throw new Error(payload.error?.message || "Could not save your appliance list.");
      profileMessage.textContent = "Saved. We’ll remember this list next time.";
      profileMessage.hidden = false;
    } catch (error) {
      profileMessage.textContent = error.message;
      profileMessage.hidden = false;
    } finally {
      button.disabled = false;
    }
  }

  async function prepareAppliances() {
    try {
      const me = await fetch("/api/auth/me");
      isSignedIn = me.ok;
      profileButton.hidden = !isSignedIn;
      signInLink.hidden = isSignedIn;
      if (isSignedIn) {
        const response = await fetch("/api/account/appliances");
        if (response.ok) {
          const profile = (await response.json()).data;
          if (profile.appliances.length) {
            list.replaceChildren();
            profile.appliances.forEach((appliance) => addAppliance(appliance));
            return;
          }
        }
      }
    } catch (_error) {
      signInLink.hidden = false;
    }
    if (!list.querySelector("[data-appliance-card]")) addAppliance();
  }

  prepareAppliances();
})();

