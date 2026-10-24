(() => {
  const email = document.querySelector("#account-email");
  if (!email) return;
  const message = document.querySelector("#account-message");
  const appliancePanel = document.querySelector("#saved-appliances");
  const historyPanel = document.querySelector("#analysis-history");
  const typeLabel = document.querySelector("[data-customer-type-label]");
  const text = (tag, className, value) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = value;
    return element;
  };

  async function load() {
    const response = await fetch("/api/auth/me");
    if (!response.ok) { window.location.assign("/login"); return; }
    const user = (await response.json()).data.user;
    email.textContent = `Signed in as ${user.email}. Your records are stored on this computer.`;
    typeLabel.textContent = user.preferred_mode === "prepaid" ? "Prepaid meter" : user.preferred_mode === "postpaid" ? "Postpaid bill" : "Choose how you pay for electricity";
    const [profileResponse, historyResponse] = await Promise.all([
      fetch("/api/account/appliances"), fetch("/api/account/history"),
    ]);
    if (!profileResponse.ok || !historyResponse.ok) throw new Error("Could not load your saved account data.");
    const profile = (await profileResponse.json()).data;
    const history = (await historyResponse.json()).data.entries;
    appliancePanel.replaceChildren();
    if (!profile.appliances.length) appliancePanel.append(text("p", "helper", "No household setup saved yet. Run an analysis and choose ‘Save appliance setup’."));
    profile.appliances.forEach((appliance) => {
      const row = text("p", "breakdown-row", `${appliance.label} · ${appliance.quantity} · ${appliance.routine.hours_per_use_day} hours/use-day · ${appliance.routine.uses_per_week} days/week`);
      appliancePanel.append(row);
    });
    historyPanel.replaceChildren();
    if (!history.length) historyPanel.append(text("p", "helper", "No saved analyses yet."));
    history.forEach((entry) => {
      const date = new Date(entry.created_at).toLocaleString();
      const summary = entry.mode === "prepaid"
        ? `${entry.result.estimated_daily_consumption_kwh.toFixed(2)} kWh/day · ${entry.result.projected_duration_days == null ? "duration unavailable" : `${entry.result.projected_duration_days.toFixed(1)} estimated days`}`
        : `${entry.result.estimated_household_kwh.toFixed(2)} estimated kWh · ${entry.result.billed_consumption.units_kwh == null ? "no billed kWh" : `${entry.result.billed_consumption.units_kwh} billed kWh`}`;
      historyPanel.append(text("article", "history-card", `${entry.mode === "prepaid" ? "Prepaid plan" : "Postpaid review"} · ${date}\n${summary}`));
    });
  }

  document.querySelector("[data-logout]").addEventListener("click", async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.assign("/");
  });
  load().catch((error) => { message.textContent = error.message; message.hidden = false; });
})();
