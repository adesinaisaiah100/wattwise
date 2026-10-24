(() => {
  const choices = [...document.querySelectorAll("[data-customer-type]")];
  const message = document.querySelector("#onboarding-message");
  if (!choices.length) return;
  let selected = null;
  let busy = false;
  const editing = new URLSearchParams(window.location.search).get("edit") === "1";

  fetch("/api/auth/me").then(async (response) => {
    if (!response.ok) { window.location.assign("/login"); return; }
    const user = (await response.json()).data.user;
    if (user.preferred_mode && !editing) window.location.replace(`/${user.preferred_mode}`);
  }).catch(() => { window.location.assign("/login"); });

  choices.forEach((button) => button.addEventListener("click", async () => {
    if (busy) return;
    selected = button.dataset.customerType;
    choices.forEach((choice) => choice.setAttribute("aria-pressed", String(choice === button)));
    busy = true;
    message.hidden = true;
    button.classList.add("is-saving");
    try {
      const response = await fetch("/api/account/preferences", {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ customer_type: selected }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.success) throw new Error(payload.error?.message || "Could not save your choice.");
      window.location.assign(`/${selected}`);
    } catch (error) {
      message.textContent = error.message;
      message.hidden = false;
      busy = false;
      button.classList.remove("is-saving");
    }
  }));
})();
