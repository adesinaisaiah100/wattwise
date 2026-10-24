$ErrorActionPreference = "Stop"

$llamaCommand = Get-Command "llama.exe" -ErrorAction SilentlyContinue
if ($llamaCommand) {
    $llama = $llamaCommand.Source
} else {
    $package = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Directory -Filter "ggml.llamacpp_*" -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $package) {
        throw "Could not find llama.cpp. Install it with: winget install llama.cpp"
    }
    $llama = Join-Path $package.FullName "llama.exe"
}

if (-not (Test-Path -LiteralPath $llama)) {
    throw "llama.exe was not found at $llama"
}

& $llama serve -hf "Qwen/Qwen3-0.6B-GGUF:Q8_0" --host "127.0.0.1" --port 8080

