# WattWise submission checklist

Use this alongside [Phase 10](../phases/10-documentation-demo-release.md). This list separates work prepared in the repository from decisions or demonstrations that still need the project team.

## Prepared in the repository

- [x] Standard README explains both customer journeys, AI role, architecture, setup, configuration, usage, tests, privacy, limitations, and repository layout.
- [x] Windows, macOS, and Linux model start instructions are documented; Windows PowerShell and POSIX shell helpers are included.
- [x] API, system design, implementation phases, and synthetic prepaid/postpaid fixtures are linked.
- [x] Synthetic demo walkthrough covers prepaid, postpaid, routine recalculation, and model-unavailable behavior.
- [x] Model and direct dependencies are identified; model weights and local secrets are excluded by `.gitignore`.
- [x] Focused code comments explain current-meter-balance semantics, postpaid reading derivation, local signing-key persistence, and model-plan verification.

## Complete before public or hackathon submission

- [ ] Choose and add a WattWise project license. No project license is currently declared.
- [ ] Review the starter repository's current license and acknowledge any files actually reused. WattWise is implemented with Flask/HTML; do not assume the starter's license applies to WattWise.
- [ ] Run the documented automated and HTTP smoke checks on the target demo computer; also test model startup and model-offline fallback.
- [ ] Rehearse the two synthetic user journeys on the target computer and record screenshots plus a short backup video.
- [ ] Set the intended GitHub remote and confirm that only intended source/docs are tracked. Keep `.env`, `instance/`, customer bills, credentials, and model weights out of the submission.
- [ ] Have both student contributors review the README's claims, demo numbers, model disclosure, and final acknowledgement wording.
