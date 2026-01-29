#!/bin/bash
# AgentY Model Runtime Launcher
# Downloads Qwen2.5-Coder-7B (GGUF) and starts llama.cpp server

set -e

MODEL_DIR="$HOME/models"
MODEL_NAME="qwen2.5-coder-7b-instruct-q4_k_m.gguf"
MODEL_PATH="$MODEL_DIR/$MODEL_NAME"
PORT=8080

echo "=== AgentY Model Runtime ==="

# Check if llama-server is installed
if ! command -v llama-server &> /dev/null; then
    echo "Error: llama-server not found. Install with:"
    echo "  brew install llama.cpp"
    exit 1
fi

# Create model directory
mkdir -p "$MODEL_DIR"

# Download model if not present
if [ ! -f "$MODEL_PATH" ]; then
    echo "Model not found. Downloading Qwen2.5-Coder-7B..."
    
    if command -v huggingface-cli &> /dev/null; then
        huggingface-cli download Qwen/Qwen2.5-Coder-7B-Instruct-GGUF \
            "$MODEL_NAME" \
            --local-dir "$MODEL_DIR"
    else
        echo "huggingface-cli not found. Install with: pip install huggingface_hub"
        echo "Or download manually from: https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF"
        exit 1
    fi
fi

echo "Starting llama.cpp server on port $PORT..."
echo "Model: $MODEL_PATH"

# Start the server with Metal GPU acceleration (Mac)
# -ngl 99 = offload all layers to GPU
# --host 127.0.0.1 = local only (security)
llama-server \
    -m "$MODEL_PATH" \
    --host 127.0.0.1 \
    --port "$PORT" \
    -ngl 99 \
    -c 8192 \
    --threads 8

echo "Model server stopped."
