#!/usr/bin/env sh
set -eu

if ! command -v llama >/dev/null 2>&1; then
  echo "llama.cpp command not found. Install llama.cpp and reopen this terminal." >&2
  echo "Official install guide: https://github.com/ggml-org/llama.cpp#quick-start" >&2
  exit 1
fi

# Keep the model endpoint on loopback; the Flask adapter expects port 8080.
exec llama serve -hf "Qwen/Qwen3-0.6B-GGUF:Q8_0" --host 127.0.0.1 --port 8080
