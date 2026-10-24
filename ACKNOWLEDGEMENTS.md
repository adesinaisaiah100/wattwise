# Acknowledgements and open-source disclosures

This file records the significant models, tools, dependencies, and project references used by WattWise. Check upstream license terms before redistributing any third-party material.

## Project license

WattWise project contributions are released under the [MIT License](LICENSE). That license does not replace the terms attached to third-party models, packages, or any separately reused source files.

## Open-weight model and inference runtime

- **Model:** [Qwen3-0.6B-GGUF](https://huggingface.co/Qwen/Qwen3-0.6B-GGUF), using the `Q8_0` quantization, from the Qwen team. The model card identifies the model license as Apache-2.0; consult the model card and license for current terms. WattWise uses the model to propose structured appliance routines and to produce optional explanations. It does not use model output as the source of energy or bill calculations.
- **Inference runtime:** [`llama.cpp`](https://github.com/ggml-org/llama.cpp), installed separately and used to serve the model locally. The upstream project is MIT-licensed.

Model weights are downloaded by the user at setup time and are not included in this repository.

## Frameworks and direct Python dependencies

- Flask, distributed under BSD-3-Clause.
- PyJWT, distributed under MIT.
- Python standard library modules provide SQLite storage, calculations, and HTTP client functionality.

Dependency versions are declared in [`requirements.txt`](requirements.txt). Follow each upstream project's license when using or redistributing those packages.

## Starter reference and implementation

- [ai-app-starter](https://github.com/victorjayeoba/ai-app-starter) was used as a learning and setup reference during early project work. WattWise's user interface is implemented with Flask-rendered HTML, CSS, and JavaScript; Gradio is not a runtime requirement. The team should confirm whether any specific source files were copied before making file-level attribution claims, and comply with the starter repository's license for any reused code.

## AI-assisted development disclosure

AI coding assistance was used during project planning, implementation, documentation, and review. The student team is responsible for reviewing, testing, understanding, and accurately presenting the submitted work and its limitations.

## Data and demo materials

The checked-in examples and demo walkthrough use synthetic household and bill values. No customer bills, private datasets, model weights, API credentials, or local account databases are included intentionally.
