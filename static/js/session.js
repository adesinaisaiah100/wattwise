(() => {
  const link = document.querySelector("[data-account-link]");
  if (!link) return;
  fetch("/api/auth/me").then((response) => {
    if (!response.ok) {
      link.textContent = "Sign in";
      link.href = "/login";
      if (window.location.pathname === "/login") {
        document.querySelectorAll("[data-mode-nav]").forEach((item) => { item.hidden = true; });
      }
      return;
    }
    return response.json().then((payload) => {
      const user = payload.data.user;
      link.textContent = "My household";
      link.href = "/account";
      document.querySelectorAll("[data-mode-nav]").forEach((item) => {
        item.hidden = Boolean(user.preferred_mode && item.dataset.modeNav !== user.preferred_mode);
        if (!user.preferred_mode) item.hidden = true;
      });
      const onboarding = document.querySelector("[data-onboarding-link]");
      if (onboarding) onboarding.hidden = Boolean(user.preferred_mode);
    });
  }).catch(() => {
    link.textContent = "Sign in";
    link.href = "/login";
    if (window.location.pathname === "/login") {
      document.querySelectorAll("[data-mode-nav]").forEach((item) => { item.hidden = true; });
    }
  });
})();
