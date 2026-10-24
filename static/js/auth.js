(() => {
  const form = document.querySelector("#auth-form");
  if (!form) return;
  const title = document.querySelector("#auth-title");
  const intro = document.querySelector("#auth-intro");
  const message = document.querySelector("#auth-message");
  const password = form.elements.password;
  const submit = form.querySelector('[type="submit"]');

  function setMode(mode) {
    form.dataset.mode = mode;
    const registering = mode === "register";
    title.textContent = registering ? "Create your account." : "Welcome back.";
    intro.textContent = registering
      ? "Your account keeps your appliance list and plans on this computer. Next, choose how your household pays for electricity."
      : "Sign in to continue to the prepaid or postpaid plan you chose for your household.";
    submit.textContent = registering ? "Create local account" : "Sign in";
    password.autocomplete = registering ? "new-password" : "current-password";
    document.querySelectorAll("[data-auth-mode]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.authMode === mode));
    });
    message.hidden = true;
  }

  document.querySelectorAll("[data-auth-mode]").forEach((button) => {
    button.addEventListener("click", () => setMode(button.dataset.authMode));
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    submit.disabled = true;
    message.hidden = true;
    const endpoint = form.dataset.mode === "register" ? "/api/auth/register" : "/api/auth/login";
    try {
      const response = await fetch(endpoint, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: form.elements.email.value, password: password.value }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.success) throw new Error(payload.error?.message || "Could not sign in.");
      const mode = payload.data.user.preferred_mode;
      window.location.assign(mode ? `/${mode}` : "/onboarding");
    } catch (error) {
      message.textContent = error.message;
      message.hidden = false;
    } finally {
      submit.disabled = false;
    }
  });
})();
