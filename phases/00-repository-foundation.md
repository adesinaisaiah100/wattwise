# Phase 00 — Repository foundation

## Outcome

Create the shared WattWise source repository and a minimal Flask application that starts reliably. The starter gives us a head start and examples, but its Gradio interface and deployment choices do not define WattWise.

## Implement

1. Create a WattWise repository from the starter template, or clone the starter into a temporary sibling folder and selectively adapt its useful files. The current workspace already contains `SYSTEM_DESIGN.md` and this `phases` folder and is not currently a Git repository, so do not try to clone directly over this non-empty folder.
2. Preserve the starter's licence and record reused code. Remove the Gradio product UI and any template-specific app branding. Do not commit a nested starter `.git` folder or vendor its history as WattWise history.
3. Establish a WattWise-owned Git repository, `.gitignore`, `README.md`, dependency file, `.env.example`, and Flask app factory/entry point.
4. Add a home route and `GET /api/health`. Return a simple healthy response without loading Qwen.
5. Add a local development command and a minimal browser page with the WattWise name and two mode choices, even if the flows are placeholders.
6. Make configuration local-first. Keep model weights, virtual environments, private `.env`, generated output, and user data out of Git.

## Components and links

- Provides the runtime foundation for every later phase.
- The health route becomes the first API smoke check in Phase 06 and the readiness check in Phase 08.
- The initial UI shell becomes the navigation/base template for Phase 06.
- Keep the current `SYSTEM_DESIGN.md` and `phases/` documentation at the WattWise project root.

## Ownership

Developer A leads repository and Flask setup. Developer B reviews that the core calculation package can be added without importing Flask or model dependencies.

## Verify and exit gate

- A clean checkout can create a Python virtual environment, install documented dependencies, and start Flask.
- Home page loads and `GET /api/health` returns the documented response.
- Git status contains no model files, secrets, customer data, or nested starter repository.
- The starter-derived files and licence acknowledgement are identifiable.

