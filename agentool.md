version: "1.0"
title: "Exhaustive Tools + Data-flows for Agentic Coding (local)"
description: >
  Comprehensive list of tools, actions, data exchanged between agents (coder, action,
  conversation), transport protocols, message schemas, permissions and example mappings.
  Intended for fully-local deployments (no cloud) and for building a forked VS Code
  agentic workflow stack.

# -----------------------------------------------------------------------
# 1) TOOL CATALOG (grouped). For each tool: purpose, allowed actions, inputs, outputs,
#    permissions required, recommended protocol (how agents call it).
# -----------------------------------------------------------------------
tools:
  editor_layer:
    - name: "Editor (VSCode fork / extension API)"
      purpose: "UI for interactive agent prompts, previews, patch application, user approvals"
      actions:
        - open_file
        - show_diff
        - apply_patch (preview + commit)
        - run_command (user-invoked)
        - manage_workspace_snapshot
      inputs: [file_path, patch_diff, run_id, metadata]
      outputs: [applied_patch_hash, user_approval, snapshot_id]
      permissions: ["workspace.read", "workspace.write", "ui.confirm"]
      protocol: "extension-api (IPC to local orchestrator)"
    - name: "Language Server Protocol (LSP)"
      purpose: "Provide semantic code info, completions, diagnostics"
      actions: [hover, completion, go-to-definition, diagnostics]
      inputs: [file_uri, position, doc_text]
      outputs: [completion_items, diagnostics, symbols]
      protocol: "LSP over stdio / TCP"
  version_control:
    - name: "Git (local CLI / libgit2)"
      purpose: "Source control authoritative store for patches and commits"
      actions: [clone, fetch, checkout, create_branch, apply_patch, commit, push, merge, revert, diff]
      inputs: [repo_url, branch, patch_diff, commit_message]
      outputs: [commit_hash, diff, merge_result, conflict_list]
      permissions: ["filesystem.write", "network (optional for push)", "gpg-sign"]
      protocol: "CLI / subprocess / libgit2 bindings (MCP wrapper recommended)"
    - name: "PR Manager (local Git server or local UI)"
      purpose: "Create and manage pull requests / review comments"
      actions: [create_pr, comment_pr, update_pr, close_pr]
      inputs: [source_branch, target_branch, title, body, commits]
      outputs: [pr_id, review_comments, merge_status]
      protocol: "HTTP REST (local) / filesystem metadata"
  filesystem_and_artifact:
    - name: "Workspace FS (sandboxed)"
      purpose: "Read/write project files in a sandbox"
      actions: [read_file, write_file, rename, delete, snapshot]
      inputs: [path, content, permissions]
      outputs: [file_hash, file_size, snapshot_id]
      permissions: ["rw on /workspace (scoped)"]
      protocol: "Local FS (MCP controlled access)"
    - name: "Artifact Store (local blob store)"
      purpose: "Store binaries, build artifacts, logs, screenshots"
      actions: [upload, download, list, delete]
      inputs: [artifact_bytes, metadata]
      outputs: [artifact_id, url]
      protocol: "Local HTTP or filesystem path"
  shell_and_execution:
    - name: "Shell Runner (sandboxed)"
      purpose: "Execute commands in isolated environment"
      actions: [run, stream_output, kill]
      inputs: [command, args, env, cwd, timeout, resource_limits]
      outputs: [exit_code, stdout, stderr, runtime_stats]
      permissions: ["execute", "network (opt-out)"]
      protocol: "MCP (JSON over stdio) or container exec API"
    - name: "Container Runner (Docker/Podman rootless)"
      purpose: "Isolated execution for tests/builds"
      actions: [start_container, exec, stop, commit_image]
      inputs: [image, command, mounts, resource_limits]
      outputs: [container_id, logs, exit_code]
      protocol: "Docker API via unix socket (MCP wrapper)"
  build_and_package:
    - name: "Build Tool (make, gradle, bazel, npm, cargo)"
      purpose: "Compile/build artifacts"
      actions: [build, clean, test-target]
      inputs: [target, flags, env]
      outputs: [build_artifact_ids, build_logs]
      protocol: "CLI via sandboxed Shell Runner"
    - name: "Package Registry (local)"
      purpose: "Store and retrieve packages (pip, npm, crates)"
      actions: [publish, fetch, list]
      inputs: [package_bundle, metadata]
      outputs: [package_id, version]
      protocol: "Local http registry"
  test_and_verification:
    - name: "Unit Test Runner (pytest, jest, junit)"
      purpose: "Run unit tests and return structured results"
      actions: [run_tests, list_tests, run_single_test]
      inputs: [test_paths, filters, timeout]
      outputs: [test_report (structured), coverage_report, artifacts]
      protocol: "CLI (json output) via Shell Runner"
    - name: "Integration Test Runner"
      purpose: "Run integration suites in containers"
      actions: [deploy_test_env, run_suite, teardown]
      outputs: [integration_report, logs]
    - name: "Mutation Testing (mutmut, cosmic-ray)"
      purpose: "Generate mutants and evaluate test suite discriminative power"
      actions: [generate_mutants, run_mutants, report]
      outputs: [mutation_score, failing_mutants]
    - name: "Property-based testing (Hypothesis, QuickCheck)"
      actions: [generate_properties, run]
  static_and_dynamic_analysis:
    - name: "Linter (flake8, eslint)"
      actions: [lint, list_rules, autofix]
      outputs: [lint_report, suggested_fixes]
    - name: "Type Checker (mypy, TypeScript tsc)"
    - name: "Static Analyzer (semgrep, clang-tidy)"
    - name: "Fuzzer (libFuzzer, AFL, honggfuzz)"
      actions: [fuzz_target, gather_crashes]
      outputs: [crash_corpus, crash_report]
    - name: "Coverage Tool (coverage.py, nyc)"
      outputs: [coverage_percentage, coverage_report]
  debugging_and_profiling:
    - name: "Debugger (gdb, lldb, node-inspect)"
      actions: [attach, breakpoint, step, dump_state]
      outputs: [stack_traces, variable_snapshots]
    - name: "Profiler (perf, pyflame)"
      outputs: [hotspots, flamegraph]
  security_and_compliance:
    - name: "Secrets Scanner (gitleaks)"
      actions: [scan_repo, report]
    - name: "Vulnerability Scanner (syft + grype, Snyk local)"
      actions: [scan_deps, report_vulns]
    - name: "SBOM generator"
      outputs: [sbom_file]
    - name: "Sandboxing engines (firejail, seccomp, gvisor)"
  orchestration_and_agents_framework:
    - name: "LangChain (local runtime)"
      purpose: "Agent orchestration, tool wrapping, memory interface"
      actions: [run_agent, register_tool, manage_memory, trace_run]
      protocol: "Python runtime + local HTTP/IPC for tools"
    - name: "Agent Orchestrator (AgentZero/Windsurf-like)"
      purpose: "Top-level flow control, retries, arbitration"
      actions: [spawn_agent, schedule, arbitrate]
      protocol: "gRPC / HTTP / local process messaging"
    - name: "MCP Gateway (Model Context Protocol-like local)"
      purpose: "Standardized tool-call protocol for models/agents to call tools"
      actions: [invoke_tool, stream_response, authorize]
      protocol: "JSON-RPC over stdio / unix socket"
  model_and_embedding:
    - name: "Model Runtime (llama.cpp, vLLM, transformers+bnb)"
      purpose: "Local model inference for tiny and medium models"
      actions: [load_model, infer, stream_tokens]
      inputs: [prompt, max_tokens, temperature, context]
      outputs: [tokens, logprobs (optional)]
      protocol: "gRPC / unix socket / local Python binding"
    - name: "Model Conversion & Quantization (gguf, ggml, bitsandbytes)"
      actions: [convert, quantize, dequantize]
    - name: "Tokenizer"
    - name: "Embedding service (local)"
      outputs: [vector]
  memory_and_kv:
    - name: "Cognee (vector + graph memory) or local Vector DB (Milvus, SQLite+FAISS)"
      purpose: "Persist PLANS, PATCH metadata, traces, embeddings"
      actions: [store, search, fetch_by_id, delete]
      inputs: [artifact, embedding, metadata, timestamp]
      outputs: [ids, search_hits]
      protocol: "HTTP + local binary protocol"
  communication_and_transport:
    - name: "JSON over stdio"
    - name: "HTTP REST (local)"
    - name: "gRPC"
    - name: "Unix socket"
    - name: "WebSocket (UI streaming)"
    - name: "Shared volume / files"
  observability_and_audit:
    - name: "Trace store (LangSmith-like local)"
      actions: [log_event, query_traces, export]
      outputs: [trace_id, timeline]
    - name: "Metrics collector (Prometheus local)"
    - name: "Audit Log (append-only, signed)"
  ui_and_cicd:
    - name: "Agent Manager Panel (VSCode)"
    - name: "Local CI Runner (act, GitHub Actions runner local)"
    - name: "Approval Gate UI"

# -----------------------------------------------------------------------
# 2) MESSAGE SCHEMAS (canonical YAML). These are the standardized messages
#    agents must exchange. Use JSON schema equivalent in implementation.
# -----------------------------------------------------------------------
message_schemas:
  meta_fields:
    - agent_id: "string (UUID)"
    - agent_role: "planner|coder|tester|reviewer|arbiter|memory|orchestrator"
    - model: "model name & version"
    - timestamp: "ISO8601"
    - run_id: "UUID"
    - parent_run_id: "UUID|null"
    - signature: "optional artifact signature (hex) for audit"
  PLAN:
    description: "High-level plan with ordered steps"
    fields:
      goal: "string"
      assumptions: ["string"]
      constraints: ["string"]
      steps:
        - id: "string"
          intent: "string"
          tool: "tool id or 'none'"
          expected_output: "string"
          cost_estimate: "ms|cpu|memory"
      artifacts: ["artifact_id"]
      confidence: "0.0-1.0"
  ACTION:
    description: "Concrete instruction to a tool (patch, command)"
    fields:
      tool: "tool id"
      command: "string or structured payload"
      inputs: "structured inputs for tool"
      expected_side_effects: "list"
      artifact_refs: ["artifact_id"]
  VERIFY:
    description: "Verification result"
    fields:
      checks: ["unit","lint","integration","mutation","property"]
      results:
        status: "pass|fail|partial"
        detail: "structured logs or artifact refs"
        metrics: {coverage: "float", mutation_score: "float"}
      evidence: ["artifact_id"]
  CONTRADICT:
    description: "Alternative implementation or counter-claim"
    fields:
      original_run_id: "UUID"
      alternative_patch: "artifact_id or inline patch"
      discriminating_tests: ["artifact_id"]
      rationale: "string"
  RESOLVE:
    description: "Arbiter decision"
    fields:
      decision: "accept|reject|iterate|escalate"
      chosen_patch: "artifact_id"
      rationale: "string"
      evidence_refs: ["artifact_id"]
  MEMORY_READ:
    fields:
      query: "string"
      top_k: "int"
    returns:
      hits:
        - id: "memory_id"
          score: "float"
          summary: "string"
  MEMORY_WRITE:
    fields:
      artifact: "artifact object"
      metadata: {tags: ["string"], timestamp: "ISO8601"}

# -----------------------------------------------------------------------
# 3) EXACT DATA TYPES / ARTIFACTS (what is transferred)
# -----------------------------------------------------------------------
data_artifacts:
  patch:
    format: "unified diff (git-style) or 'apply_patch' JSON"
    schema:
      - file: "path"
        change_type: "modify|add|delete"
        diff: "string (unified)"
  test_suite:
    format: "test file(s) + harness"
    includes: [test_files, fixtures, run_command]
  test_report:
    format: "structured JSON"
    fields: [test_counts, passed, failed, flaky, logs, exit_code]
  build_artifact:
    format: "binary or tarball"
    metadata: [build_id, commit_hash, size, checksum]
  coverage_report: {format: "lcov/json", percent: "float"}
  logs:
    format: "structured streaming"
    fields: [timestamp, level, message, context]
  embedding:
    format: "float32[]"
    dims: "int"
    metadata: [artifact_id, timestamp]
  vector_search_hit:
    fields: [id, score, snippet, metadata]
  trace:
    format: "timeline of messages + artifacts"
    fields: [run_id, events[], artifacts[]]

# -----------------------------------------------------------------------
# 4) TRANSPORTS, PROTOCOL PATTERNS, SECURITY
# -----------------------------------------------------------------------
protocols_and_transports:
  recommended_default:
    - "MCP (JSON-RPC over stdio / unix-socket) for tool calls from model/agent"
    - "gRPC for model runtime & orchestrator control"
    - "HTTP REST for UI and artifact store"
    - "Unix sockets for high-trust local services"
    - "Shared filesystem for large artifacts / caching (scoped path)"
  patterns:
    - name: "call-and-return"
      description: "agent sends ACTION -> tool executes -> returns structured result (verify)"
      transport: "MCP JSON over stdio"
    - name: "streaming"
      description: "long-running build/test streams logs back as events"
      transport: "WebSocket or gRPC streaming"
    - name: "pub-sub"
      description: "broadcast events (agent started/finished) to listeners"
      transport: "local message bus (NATS or Redis local)"
  security_controls:
    - sandboxing: "run shell and tool executions in rootless containers or user namespaces"
    - network_policy: "deny network egress by default; opt-in for specific hosts"
    - filesystem_scope: "only mount /workspace read-write; others read-only"
    - secrets: "use an encrypted local secrets store; never write secrets to logs"
    - signing: "sign artifacts with a local key; verify at merge"
    - approval_gates: "PR merge requires human approval or multi-agent consensus"
    - rate_limiting: "limit model token usage & recursive depth"
    - audit: "append-only signed audit log (timestamped)"

# -----------------------------------------------------------------------
# 5) PERMISSIONS MODEL (who can do what)
# -----------------------------------------------------------------------
permissions:
  agent_scopes:
    planner:
      allowed_tools: ["read-only fs", "memory.read", "mcp.git (read)", "orchestrator"]
      denied_tools: ["shell.run", "git.push"]
    coder:
      allowed_tools: ["mcp.fs.write (scoped)", "mcp.git.commit", "memory.write"]
      require_approval: ["git.push", "create_pr"]
    tester:
      allowed_tools: ["shell.run (tests)", "container.exec (test env)"]
    arbiter:
      allowed_tools: ["run verifier", "compare artifacts", "resolve"]
      require_human_override: ["escalate"]
    memory_agent:
      allowed_tools: ["memory.read", "memory.write", "artifact.store"]
  human_roles:
    developer:
      can_approve_merge: true
      can_override_agent: true
    release_manager:
      can_force_push: true (with audit)
  enforcement:
    mechanism: "MCP gateway enforces token-based scope & runtime sandboxing"

# -----------------------------------------------------------------------
# 6) MAPPINGS: concrete tool -> allowed agent actions & expected exchanged payloads
# -----------------------------------------------------------------------
mappings:
  GitTool:
    actions:
      - name: clone
        input: {repo_url: "string", depth: "int (optional)"}
        output: {repo_path: "string", commit_hash: "string"}
      - name: apply_patch
        input: {patch: "patch artifact or inline diff", base_ref: "branch/commit"}
        output: {commit_hash: "string", conflicts: ["file paths"]}
      - name: create_pr
        input: {source_branch, target_branch, title, body}
        output: {pr_id, pr_url}
    transfer_between_agents:
      - coder -> git: "patch (diff) + metadata"
      - orchestrator -> coder: "commit_hash, push_status"
  FileSystemTool:
    actions:
      - read_file: inputs {path} -> outputs {content, file_hash}
      - write_file: inputs {path, content, mode} -> outputs {file_hash, size}
    transfer:
      - coder -> fs: "file writes (patch applied)"
      - tester -> fs: "create temp fixtures"
  ShellTool:
    actions:
      - run: inputs {command, cwd, env} -> outputs {exit_code, stdout, stderr, runtime_stats}
    transfer:
      - tester -> shell: "run test command"
      - arbiter -> shell: "run benchmarking harness"
  ModelRuntime:
    actions:
      - infer: inputs {prompt, context, tools_schema} -> outputs {tokens, tool_calls}
      - stream: streaming tokens
    transfer:
      - conversation_agent -> model: "system+user+assistant context"
      - model -> orchestrator: "tool_call structured payload"
  MemoryTool (Cognee):
    actions:
      - store: inputs {artifact, embedding, metadata} -> outputs {memory_id}
      - search: inputs {query_vector, top_k} -> outputs {list of hits}
    transfer:
      - any_agent -> memory: "PLAN, PATCH summary, VERIFY logs"
      - other_agent -> memory: "read past decisions"

# -----------------------------------------------------------------------
# 7) AGENT-TO-AGENT INTERACTIONS (protocol-level: what is explicitly transferred)
# -----------------------------------------------------------------------
agent_interaction_definitions:
  typical_round_trip:
    - step: "PLAN"
      sender: "PlannerAgent"
      payload:
        - goal
        - steps[]
        - constraints
        - expected_artifacts[]
        - plan_id
    - step: "ACTION"
      sender: "CoderAgent"
      payload:
        - patch_artifact_id
        - branch
        - patch_summary
    - step: "VERIFY"
      sender: "TesterAgent"
      payload:
        - test_report_id
        - coverage
        - failing_tests[]
    - step: "CONTRADICT"
      sender: "ContradictorAgent"
      payload:
        - alternative_patch_id
        - discriminating_tests_id
        - rationale
    - step: "ARBITRATE / RESOLVE"
      sender: "ArbiterAgent"
      payload:
        - decision
        - chosen_artifact_id
        - evidence_refs[]
        - vote_summary (if multi-agent)
    - step: "MEMORY_WRITE"
      sender: "Any agent"
      payload:
        - store references to artifacts and summary
  payload_contracts:
    - contract: "artifact references are canonical ids; actual artifact binary remains in artifact store"
    - contract: "agents must reference memory ids, not raw content, for large blobs"
    - contract: "tool calls must be idempotent or contain a run_id to deduplicate"

# -----------------------------------------------------------------------
# 8) EXAMPLE END-TO-END FLOW (compact)
# -----------------------------------------------------------------------
example_flow:
  - "Dev triggers 'Add feature X' in VSCode (UI) -> sends PLAN to orchestrator"
  - "PlannerAgent (Mistral-small) returns PLAN with steps"
  - "Orchestrator spawns CoderAgent (Qwen2.5-Coder-7B / StarCoder2-7B), passes plan + tools schema"
  - "CoderAgent produces patch artifact -> stores patch in artifact store, writes memory entry"
  - "Orchestrator invokes TesterAgent to run tests (containerized) -> returns test_report"
  - "If tests fail -> ContradictorAgent proposes alt patch + discriminating tests"
  - "ArbiterAgent runs A vs B -> selects winner (RESOLVE)"
  - "If RESOLVE == accept -> create local PR (GitTool create_pr) but block push until human approval"
  - "All messages & artifacts written to Cognee and Trace store (signed audit)"

# -----------------------------------------------------------------------
# 9) RECOMMENDATIONS / BEST PRACTICES (summarized)
# -----------------------------------------------------------------------
best_practices:
  - "Standardize message schema (PLAN/ACTION/VERIFY/CONTRADICT/RESOLVE/MEMORY) as above"
  - "Use MCP gateway to centralize tool authorization & auditing"
  - "Keep recursion depth limited and cost-estimated in PLAN"
  - "Prefer small specialized models for repeated micro-tasks (3B–8B) and reserve larger models for meta-reasoning"
  - "Always sign and timestamp final artifacts before merge"
  - "Use deterministic replay for arbiter decisions (re-run with recorded seed/env)"
  - "Store lightweight summaries in memory and heavy blobs in artifact store"
  - "Require human approval for network/remote pushes"
  - "Encrypt memory at rest and secure access with local keys"

# -----------------------------------------------------------------------
# 10) QUICK INDEX (for implementation mapping)
# -----------------------------------------------------------------------
index:
  - "Implement MCP gateway first (tool authorization + sandbox enforcement)"
  - "Wrap Git, FS, Shell as MCP tools with the exact input/output contracts above"
  - "Plug models via a local ModelRuntime service exposing 'infer' and 'tool_call' hooks"
  - "Implement Cognee-compatible Memory API honoring MEMORY_READ/MEMORY_WRITE"
  - "Add trace/audit store with signed logs"
  - "Build VS Code Agent Manager to display runs/traces and request approvals"

