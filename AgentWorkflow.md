# Comprehensive Agentic Coding Workflow (Local VS Code Fork)

This document provides a **comprehensive workflow** for various agents (Cursor, Windsurf, GitHub Copilot, Antigravity IDE, OpenAI Agent, Claude Code, AgentZero), plus the architecture for forking VS Code to execute **100% local**, recursive, code-oriented small models. It features **Cognee** for persistent memory and **LangChain** for orchestration.

For each agent, I detail: precise role, inputs/outputs, code actions (edit, PR, run tests...), verification loops, conversation protocols (challenge/contradiction), MCP/LangChain integration, runtime requirements (gguf/llama.cpp, MLX, vLLM, quantization), and security risks.

**Key Sources**: MCP/Claude docs, Cognee, LangChain, Windsurf, Code Llama / StarCoder.

---

## Common Rules for All Workflows (Definitions)

*   **Primitive Action**: Atomic operations executable by agents (e.g., `read-file`, `write-file`, `run-tests`, `format`, `run-linter`, `run-shell`, `open-pr`, `create-branch`, `run-static-analysis`, `run-fuzz`).
*   **Cycle (PLAN → ACT → VERIFY → REVISE)**: Every agent follows this strict pattern. Steps are standardized in JSON (see "Standardized Messages" below) to facilitate automatic verification.
*   **Standardized Messages** (Simplified Examples):
    *   `{"type":"PLAN","goal":"...","steps":["..."]}`
    *   `{"type":"ACTION","tool":"edit","target":"file","patch":"diff/unified"}`
    *   `{"type":"VERIFY","checks":["unit","lint","ci"],"results":{}}`
    *   `{"type":"RESOLVE","decision":"accept|reject","rationale":"..."}`
*   **Memory**: [Cognee](https://github.com/topoteretes/cognee) stores artifacts (plans, patches, diffs, tests, decisions) as vectors + graphs (temporal index, dependencies).
*   **Orchestrator**: LangChain (or LangGraph) orchestrates agents as *tools/subagents*, providing `Memory` and traces (LangSmith-style) for debugging and evaluation.

---

## Local Implementation Format (100% Local Constraints)

*   **Recommended Models (Small, Code-Focused)**:
    *   **Qwen2.5-Coder (7B)** or **DeepSeek-R1-Distill (8B)**: State-of-the-art performance for local code generation.
    *   **StarCoder2 (3B/7B)** and **Code Llama (7B)**: Excellent alternatives for low-latency inference.
    *   **Optimization**: Quantize to GGUF (4-bit/8-bit) or MLX format (for Apple Silicon).
*   **Runtimes**:
    *   **macOS (Apple Silicon)**: `llama.cpp` (server) or `MLX` framework are recommended for native GPU acceleration.
    *   **Linux/NVIDIA**: `vLLM` or `transformers+bitsandbytes`.
    *   **Packaging**: Ollama or local Docker containers.
    *   *Note*: vLLM support on macOS is experimental/CPU-limited; stick to llama.cpp/MLX for performance.
*   **MCP & Transports**: Implement local MCP servers (stdio / unix-socket / localhost) for sensitive tools (git, fs, shell). Always sandbox (chroot, user namespaces, Docker) any MCP server exposing shell/git access.

---

## Detailed Workflows by Agent

### 1) Cursor — *Interactive Editing & Exploration Agent*

*   **Precise Role**: Facilitate code modifications within the editor, offer contextual completions, create mini-plans, and previews.
*   **Concrete Actions**: Open file, propose patch, apply patch in preview, start local test env (server), snapshot workspace.
*   **Conversation & Challenge**: Creates two "passes" — **Proposal** (PLAN+PATCH) and **Control** (VERIFY). If VERIFY fails, generates `RESOLVE` with a correction plan.
*   **LangChain/Cognee Integration**: Cursor acts as the UI Agent (client); saves plans/snapshots to Cognee for context recall.
*   **Local Runtime**: Small model (e.g., Qwen2.5-Coder 7B) in GGUF for low latency.

---

### 2) Windsurf (Cascade Agent) — *Autonomous Multi-Step Agent*

*   **Precise Role**: "Cascade" agent planning multiple coding iterations, capable of executing, correcting, and simulating ~10 steps ahead.
*   **Concrete Actions**: Global plan, create branches, write tests, fix errors via successive patches, open draft PR.
*   **Verification Loop**: Executes `unit`, `integration`, `fuzz` according to plan; if divergent, activates "root-cause" subagent producing contradictory hypotheses and targeted tests.
*   **Localization**: Package Windsurf-like logic into local microservices (MCP servers); execute agent engine on local GPU if available, otherwise use small CPU models.
*   **Security**: Keep Shell/Git MCP behind isolated processes; require user approval for pushes.

---

### 3) GitHub Copilot / Copilot CLI — *Task Executor & PR Automation*

*   **Precise Role**: Completions, snippet generation, task automation via CLI (delegation to background agents).
*   **Actions**: Generate snippet, open PR, run `copilot test` (headless CLI), create commit.
*   **Challenge Pattern**: "Delegate" creates a draft PR + runs CI; a **Verifier Agent** (local StarCoder) reads the PR and produces a `VERIFY` summary; if contradictions found, leaves comments on PR and creates follow-up commits.

---

### 4) Google Antigravity (Agent-First IDE) — *Multi-Agent Manager (Editor + Mission Control)*

*   **Precise Role**: Manager of multi-agents, artifacts (screenshots, recordings), and "Mission Control" view for coordinating agents.
*   **Actions**: Assign sub-agents (Formatter, Test-Runner, Refactorer), preserve Artifacts (task lists, recordings) stored in Cognee; agents communicate via local event bus.
*   **Contradiction Protocol**: Agents publish *claims* (patch + evidence); an *Arbiter* (lightweight agent) runs claims in isolation and accepts/rejects. Artifacts + diffs are logged in Cognee for audit.

---

### 5) OpenAI Agent Builder / AgentKit — *Visual Workflow & Exportable*

*   **Precise Role**: Visual workflow designer, exporting locally executable SDKs; useful as "design-to-runtime".
*   **Actions**: Builder nodes (Plan, ToolCall, Verify), export to JSON SDK, execute via local runtime (Node/Python adapter). Use exported code as a template for VS Code extension actions.
*   **Local Integration**: Convert Agent Builder nodes into LangChain flows (LangGraph) + map tools to local MCP endpoints.

---

### 6) Claude Code (Terminal Agent + MCP) — *Dev-Oriented CLI Agent*

*   **Precise Role**: CLI agent capable of acting on filesystem/git, exposing tools via MCP, plugins (skills/hooks), and acting as an MCP server.
*   **Actions**: `read`, `edit`, `bash`, `test`, `create-pr`, `review`. Lifecycle hooks execute scripts before/after sessions.
*   **Security Protocol / MCP**: Uses MCP to connect tools (Git, DB, Filesystem); docs/implementations show client/server stdio patterns.
*   **Contradiction / Agent Duel**: Configure named subagents (e.g., `linter-agent` vs `refactor-agent`); upon disagreement, execute arbitration script: run tests + static analysis + run diff-based behavioral tests; store decision in Cognee.

---

### 7) AgentZero — *Deterministic Execution & Reliable Orchestration*

*   **Precise Role**: Provide reliable architecture for "end-to-end" agent execution, dynamic tool creation, and deterministic runs.
*   **Actions**: Agent composition, execution orchestration, fallback deterministic logic (re-run with stricter assertions).
*   **Local Usage**: Use AgentZero (running in Docker) to orchestrate reproducible executions (local CI), run monitoring, and rollbacks.

---

## How Agents "Challenge" Each Other — Comprehensive Protocol

1.  **Propose (Agent A)**: Sends `PLAN` + `PATCH` + `EVIDENCE` (tests to run).
2.  **Verify (Agent B)**: Executes tests in sandbox, returns `VERIFY` with pass/fail + logs.
3.  **Contradict (Agent C)**: Reads patch, proposes *alternative patch* + *focused tests* that differentiate behaviors (mutation tests / property tests).
4.  **Arbiter**: Executes A vs C on the same harness; compares coverage, performance, invariants; logs decision.
5.  **Meta-Loop**: If inconclusive, spawns recursive subagents (tiny models) to generate more focused tests until time zero or budget exhausted.
6.  **Audit**: All messages + evidence versioned in Cognee (vector+graph) for research and explainability.

---

## Cognee Integration (Memory) — Concrete Pattern

*   **What is Stored**: Plans (`PLAN` JSON), patches (diffs), verifications (`VERIFY` logs), decisions (`RESOLVE`), artifacts (build logs, screenshots).
*   **Access**: Agents request `memory.query("recent-plan for file X")` → Cognee returns top-K vectors + graph neighbors (dependency chain).
*   **Use-Cases**: Avoid repeating tests, recall past decisions, retrieve "why this refactor" for reviewers.
*   **Security**: Encrypt memory at rest (local keys); limit scope by repo/team.
*   **Implementation**: Use `langchain-cognee` or `cognee-integration-langgraph` for native Python integration.

---

## LangChain Mapping (Implementation)

*   **Agent** → `Agent` / `Tool` (LangChain); each primitive action is a `Tool` exposed via an MCP wrapper.
*   **Memory** → `CogneeRetriever` or Custom Component: Implements vector+graph storage.
*   **Workflows** → LangGraph workflows (predetermined flows) or standard LangChain agents (dynamic). Use traces (LangSmith-style) for observability.

---

## Technical Architecture — VS Code Fork (Key Components)

1.  **Core Editor**: VS Code fork (Electron) or native extension.
2.  **Agent Manager Panel** (Mission Control): Lists agents, runs, artifacts; allows approve/rollback.
3.  **MCP Gateway** (Local Process): A Node/Python process exposing MCP servers for tools (git, fs, shell, test-runner). All MCP services run in isolated subprocesses.
4.  **Model Runtime Layer**:
    *   **Mac**: Dockerized or local process wrappers for `llama.cpp` (server mode) or `MLX-server`.
    *   **API**: Expose OpenAI-compatible endpoints or gRPC.
    *   **Artifacts**: Provide GGUF quantized models (Qwen2.5/StarCoder2).
5.  **LangChain Orchestrator**: Local Python service orchestrating agents, Cognee memory calls, and exposing HTTP/WS for UI.
6.  **Sandbox & Security**: Each tool runs in a container/user-ns; MCP requires explicit scopes; deny network by default unless allowed.
7.  **Plugin System**: Package skills as installable extensions.

---

## Example End-to-End Flow (Concrete)

1.  **Trigger**: Dev clicks "Agent: Add feature X" in VS Code fork.
2.  **Plan**: UI sends `PLAN` to Orchestrator (LangChain).
3.  **Orchestrate**: Orchestrator creates branch via Git-MCP, spawns `planning-agent` (Mistral/Qwen) → PATCH v0.
4.  **Act**: `action-agent` (StarCoder2/Qwen-Coder) applies patch in sandbox FS via MCP.
5.  **Test**: `test-agent` executes unit suite in container; returns FAIL on test T1.
6.  **Fix**: `fix-agent` generates targeted patch + new test; `verify-agent` re-runs.
7.  **Arbitrate**: If `fix-agent` and `test-agent` disagree, spawn `arbiter-agent` to run mutation tests.
8.  **Resolve**: Final accepted patch pushed to local remote; PR draft created; Cognee stores full trace.

---

## Security, Limits, and Practical Recommendations

*   **Sandbox Shell/Git MCP**: Never expose these without sandboxing (Docker, chroot, seccomp).
*   **Model Budget**: Prioritize small models (3B–8B) for subagents and tests. Reserve larger models (14B-30B+) for heavy planning only if local hardware allows.
*   **Heavy Testing**: Automate mutation/property tests to differentiate concurrent patches.
*   **Observability**: Full trace (LangSmith-compatible) + artifacts in Cognee for audits.

---

## Immediate Deliverables

I can produce the following immediately:

1.  **Architecture Diagram**: VS Code Fork + MCP + LangChain + Cognee + Runtimes.
2.  **JSON Schema**: Standard messages (PLAN/ACTION/VERIFY/RESOLVE).
3.  **MCP Security Playbook**: Checklist for secure local implementation.
4.  **LangChain Agent Template**: Python + MCP Tool Mapping boilerplate.
5.  **Model/Quantization Checklist**: Recommendations for GGUF/MLX vs vLLM.

---

### Ready-to-Use Artifacts (VS Code Fork, 100% Local, LangChain+MCP+Cognee)

#### 1) Standard Agent Message Schema (Canonical JSON)

> **Goal**: Auditability, Explicit Contradiction, Controlled Recursion

```json
{
  "meta": {
    "agent_id": "string",
    "agent_role": "planner|coder|tester|reviewer|arbiter|memory",
    "model": "string",
    "timestamp": "iso8601",
    "run_id": "uuid",
    "parent_run_id": "uuid|null"
  },
  "message": {
    "type": "PLAN|ACTION|VERIFY|CONTRADICT|RESOLVE|MEMORY_WRITE|MEMORY_READ",
    "goal": "string",
    "assumptions": ["string"],
    "inputs": {
      "files": ["path"],
      "context_refs": ["memory_id"],
      "constraints": ["string"]
    },
    "steps": [
      {
        "id": "step-1",
        "intent": "string",
        "tool": "mcp.git|mcp.fs|mcp.shell|none",
        "expected_output": "string"
      }
    ],
    "artifact": {
      "type": "diff|test|log|decision",
      "content": "string",
      "hash": "sha256"
    },
    "verification": {
      "checks": ["unit","lint","integration","mutation"],
      "results": {
        "status": "pass|fail",
        "evidence": ["log_ref"]
      }
    },
    "decision": {
      "status": "accept|reject|iterate",
      "rationale": "string",
      "next_action": "string"
    }
  }
}
```

**Key Points**:
*   **Contradiction** must be a mandatory `CONTRADICT` message.
*   **Acceptance** must cite **executed evidence**.
*   `parent_run_id` enables **recursion**.

#### 2) LangChain Template (Python) — Agent + MCP + Cognee

**2.1 Cognee Memory Interface (LangChain Adapter)**

```python
from langchain.schema import BaseMemory
# Note: Pseudocode adaptation; use official langchain-cognee package in production
class CogneeMemory(BaseMemory):
    def __init__(self, client):
        self.client = client
        self.memory_key = "history"

    def load_memory_variables(self, inputs):
        query = inputs.get("query", "")
        # Retrieve top-k semantic hits + graph neighbors
        return {
            self.memory_key: self.client.search(query, top_k=5)
        }

    def save_context(self, inputs, outputs):
        self.client.store({
            "inputs": inputs,
            "outputs": outputs
        })
    
    def clear(self):
        pass
```

**2.2 Generic MCP Tool (Shell/Git/FS)**

```python
from langchain.tools import BaseTool
import subprocess
import json

class MCPTool(BaseTool):
    name = "mcp_tool"
    description = "Call local MCP server via stdio"

    def _run(self, payload: dict):
        # Example of calling a local MCP process via stdio
        proc = subprocess.Popen(
            ["mcp-client", "--json"], # hypothetical CLI wrapper
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = proc.communicate(json.dumps(payload).encode())
        if proc.returncode != 0:
            return f"Error: {stderr.decode()}"
        return stdout.decode()
```

**2.3 Recursive Coder Agent (Tiny Model)**

```python
from langchain.agents import initialize_agent, AgentType
from langchain_community.llms import LlamaCpp

# Use LlamaCpp for local GGUF models (efficient on CPU/Mac)
llm = LlamaCpp(
    model_path="./models/qwen2.5-coder-7b-instruct-q4_k_m.gguf",
    n_ctx=4096,
    temperature=0.2,
    verbose=True
)

agent = initialize_agent(
    tools=[MCPTool()],
    llm=llm,
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    memory=CogneeMemory(client=cognee_client), # Connect to Cognee
    verbose=True
)
```

#### 3) Contradiction Protocol (Mandatory)

**Rule**: No code merge without at least one *executed contradiction*.

**Concrete Pattern**:
1.  **CoderAgent**: Generates Patch + Tests.
2.  **TesterAgent**: Runs Tests → FAIL/PASS.
3.  **ContradictorAgent**: Proposes **Alternative Implementation** + **Discriminatory Tests** (Mutation/Property).
4.  **ArbiterAgent**: Runs A vs B. Compares coverage, invariants, performance.
5.  **Resolve**: `accept | reject | iterate`. Stored in Cognee.

#### 4) Minimal Agent Roles (Recommended)

| Agent | Model (Local) | Exact Responsibility |
| :--- | :--- | :--- |
| **Planner** | Mistral Small / Qwen-7B | Plan, Hypotheses |
| **Coder** | Qwen2.5-Coder-7B / StarCoder2-3B | Precise Patching |
| **Tester** | CodeLlama-7B / Qwen-Coder | Tests, Execution |
| **Contradictor** | Qwen2.5-Coder-7B | Alternative + Mutation |
| **Arbiter** | Mistral Small | Final Decision |
| **Memory** | — | Cognee Only |

**Summary**: All small models, controlled recursion, **100% Local**.

#### 5) MCP Security (Essential Checklist)

*   [ ] MCP Shell running in **rootless container**.
*   [ ] **No network access** by default.
*   [ ] Filesystem mounted **Read-Only** (except scoped `/workspace`).
*   [ ] Human confirmation required for `git push`.
*   [ ] MCP Logs hashed -> stored in Cognee.
