# Recommended Local Models for Code Generation (2025/2026 Update)

Here is a concise summary of the best **local** options for code generation and execution, updated for the current ecosystem.

### Core Recommendations

1.  **Code-Focused (Best Balance of Quality/Scale)**:
    *   **Qwen2.5-Coder (7B - 32B)**: Currently widely regarded as the SOTA for local coding models. Excellent instruction following and widespread language support.
    *   **DeepSeek-Coder-V2 / R1-Distill versions**: Exceptional performance on reasoning and complex coding tasks.
    *   *Legacy/Solid*: **Code Llama (7B–34B)** remains a robust baseline.

2.  **Pure Open-Source (Code Specialized)**:
    *   **StarCoder2 (3B / 7B / 15B)**: Excellent on benchmarks (HumanEval/MBPP) and ideal for strict FOSS requirements. Good for code infilling.

3.  **Compact / Local-First (Low Latency)**:
    *   **Qwen2.5-Coder 1.5B / 3B**: Incredible performance-per-parameter. Runs comfortably on older laptops.
    *   **StarCoder2 3B**: Good compromise for background agents.

4.  **Agentic Workflows & Execution**:
    *   **Mistral (Nemo / Small 24B)**: Optimized for instruction-following and agentic behaviors (function calling).
    *   **Llama 3.1 (8B / 70B)**: Strong generalist model with excellent tool-use capabilities.

5.  **Multi-Model Hubs (Testing)**:
    *   **OpenRouter / local-ai**: Useful proxy layers if you want to test API compatibility before full local download.

### Runtime Recommendations (Hardware Specific)

*   **macOS (Apple Silicon M1/M2/M3/M4)**:
    *   **Best Option**: **`llama.cpp`** (GGUF format) or **`MLX`** (Apple's framework).
    *   *Why*: Native Metal (GPU) acceleration. `vLLM` is currently CPU-bound or experimental on Mac and generally much slower.
*   **Linux / NVIDIA GPU**:
    *   **Best Option**: **`vLLM`** or **`transformers`** + **`bitsandbytes`**.
    *   *Why*: Maximum throughput and batching performance.

### Practical Tip for Developers
Start with **Qwen2.5-Coder-7B** (GGUF Q4_K_M) on `llama.cpp`. It fits in ~6GB VRAM, is very fast, and outperforms many older, larger models. Use **Mistral** or **Llama 3.1** for the Orchestrator/Planner agent.
