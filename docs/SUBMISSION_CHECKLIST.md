# WattWise submission checklist

Use this alongside [Phase 10](../phases/10-documentation-demo-release.md) and the official OPEN//BUILD 2026 Challenge Brief. The brief requires a judge-accessible GitHub repository; a working demonstration or clear run instructions; a README with setup/reproduction instructions and dependencies; an explanation of the model, its role, selection, and limitations; and acknowledgements for licenses, datasets, reused code, external resources, and significant AI-assisted work. The official form will request project name, both team members and universities, problem and solution descriptions, repository/demo links, model information, documentation, and acknowledgements.

## Prepared in the repository

- [x] Standard README explains both customer journeys, AI role, architecture, setup, configuration, usage, tests, privacy, limitations, and repository layout.
- [x] Windows, macOS, and Linux model start instructions are documented; Windows PowerShell and POSIX shell helpers are included.
- [x] API, system design, implementation phases, and synthetic prepaid/postpaid fixtures are linked.
- [x] Synthetic demo walkthrough covers prepaid, postpaid, routine recalculation, and model-unavailable behavior.
- [x] Model and direct dependencies are identified; model weights and local secrets are excluded by `.gitignore`.
- [x] Focused code comments explain current-meter-balance semantics, postpaid reading derivation, local signing-key persistence, and model-plan verification.
- [x] Public GitHub repository with a top-level MIT license and a dedicated open-source acknowledgements/disclosure file.
- [x] README contains setup, run, test, reproduction, model, dependency, and known limitation information.

## Complete before hackathon form submission

- [ ] Complete the official form with project name, full names of both members, universities, problem statement, solution description, GitHub URL, working demo/video or run instructions, model details, documentation, and acknowledgements.
- [ ] Run the documented automated and HTTP smoke checks on the target demo computer; test local model startup and model-offline fallback.
- [ ] Rehearse the two synthetic user journeys on the target computer. Prepare a working demo link, or a short video if useful; the brief accepts a live demo link, demo video, or clear instructions for running the prototype.
- [ ] Confirm the public repository and any demo links are accessible to judges. Keep `.env`, `instance/`, customer bills, credentials, and model weights out of the submission.
- [ ] Have both student contributors verify their team details, claims about their contributions, demo results, model disclosure, third-party license compliance, and acknowledgement wording.
- [ ] Monitor the OSCA Ile-Ife community for the official form and any submission or demo-day updates.
