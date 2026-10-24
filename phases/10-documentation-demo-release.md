# Phase 10 — Documentation and demo release

## Outcome

Package WattWise so a judge, teammate, or new contributor can understand what it does, run it locally, inspect its model use, and reproduce the two MVP journeys.

## Implement

1. Update the main README with problem, target users, prepaid/postpaid workflows, limits, architecture diagram, screenshots, and project status.
2. Write a clean Windows-first local setup: Python environment, dependency install, start `llama.cpp` server with Qwen, start Flask, open the browser, and troubleshoot common startup issues. State which steps need internet and that weights remain outside Git.
3. Document the API schemas/routes and include copyable sample requests and responses.
4. Disclose the Qwen model/repository, quantization, Apache-2.0 licence, its role as an explanation layer, limitations, and the fact that Nigerian Pidgin quality is not assumed.
5. Record third-party dependencies, starter code reuse/licence, project licence, data/source acknowledgements, and any required hackathon acknowledgements.
6. Prepare synthetic demo data only. Show one prepaid routine planning case, one postpaid comparison, how a routine edit changes calculated results, and behavior when Qwen is stopped.
7. Record a video backup if the live laptop/network/model download is unreliable. Keep the demo short and reproducible.

## Components and links

- Uses completed flows and test evidence from Phases 04–08.
- Documentation must not promise OCR, billing integrations, fraud detection, or model capabilities the MVP does not provide.

## Ownership

Developer A coordinates README, API, and run docs. Developer B reviews formula explanations and sample outputs. Both review model/licence disclosure and rehearse the demo.

## Verify and exit gate

- A new person can follow the instructions from a clean checkout.
- The sample data reproduces the displayed values.
- Repository contains no secrets, personal customer bills, model weights, or temporary build artifacts.
- Live or recorded demo clearly shows both complete customer journeys and the system's uncertainty/fallback behavior.

