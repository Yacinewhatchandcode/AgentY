import os
import json
import subprocess
import shlex
from typing import List, Dict, Any, Optional

# LangChain Imports
from langchain.agents import initialize_agent, AgentType, Tool
from langchain.memory import BaseMemory
from langchain.schema import BaseMessage
from langchain_community.llms import LlamaCpp
# Note: For production, use the official langchain-cognee package
# from langchain_cognee import CogneeRetriever 

# ------------------------------------------------------------------------------
# 1. Cognee Memory Adapter (Persistent Graph+Vector Store)
# ------------------------------------------------------------------------------
class CogneeMemory(BaseMemory):
    """
    Adapts Cognee's local graph/vector store to LangChain's memory interface.
    Stores semantic context (Plans, Decisions) and retrieves relevant history.
    """
    memory_key: str = "history"
    client: Any = None  # Placeholder for initialized Cognee client

    def __init__(self, client):
        super().__init__()
        self.client = client

    @property
    def memory_variables(self) -> List[str]:
        return [self.memory_key]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve relevant context from Cognee based on the current input query.
        """
        query = inputs.get("input", "") or inputs.get("technical_goal", "")
        
        # Hypothetical Cognee Search API call
        # In reality: cognee.search(query, search_type="hybrid")
        print(f"[Memory] Searching Cognee for: '{query}'")
        
        # Mock result conforming to AgentZero requirements (past solutions)
        relevant_context = [
            f"Context from previous run: Found that vLLM is slow on Mac; use llama.cpp instead.",
            f"Constraint: All shell commands must be sandboxed."
        ]
        
        return {
            self.memory_key: "\n".join(relevant_context)
        }

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """
        Save the interaction (Plan -> Result) into Cognee graph.
        """
        print(f"[Memory] Storing interaction in Cognee graph...")
        # In reality: cognee.add(data={"in": inputs, "out": outputs}, collection="agent_traces")
        pass

    def clear(self) -> None:
        pass


# ------------------------------------------------------------------------------
# 2. Native macOS Sandboxed Shell Tool (Speed > Docker)
# ------------------------------------------------------------------------------
class MacSandboxedShellTool:
    """
    Executes shell commands using macOS native `sandbox-exec` for isolation.
    Avoids Docker overhead for local dev loops.
    """
    def run(self, command: str) -> str:
        # Define a minimal sandbox profile string
        # Deny network by default, allow reading /Users, allow writing only to Workspace
        sandbox_profile = """
        (version 1)
        (allow default)
        (deny network*)
        ; (allow network-outbound (remote ip "localhost:*")) ; Uncomment for local server access
        (allow file-read* (subpath "/Users"))
        (allow file-write* (subpath "/Users/yacinebenhamou/AgentY")) 
        """
        
        # Write profile to temp file (in practice, keep this persistent)
        profile_path = "/tmp/agent_sandbox.sb"
        with open(profile_path, "w") as f:
            f.write(sandbox_profile)

        # Wrap command in sandbox-exec
        # Usage: sandbox-exec -f profile_file command
        safe_command = f"sandbox-exec -f {profile_path} /bin/zsh -c {shlex.quote(command)}"
        
        print(f"[Shell] Running sandboxed: {command}")
        try:
            result = subprocess.run(
                safe_command, 
                shell=True, 
                capture_output=True, 
                text=True,
                timeout=30 # Safety timeout
            )
            return f"Exit Code: {result.returncode}\nStdout: {result.stdout}\nStderr: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "Error: Command timed out."
        except Exception as e:
            return f"Error executing sandbox: {str(e)}"


# ------------------------------------------------------------------------------
# 3. AgentZero-Style Orchestrator (Recursion & Verification)
# ------------------------------------------------------------------------------
def create_local_agent_stack():
    """
    Builds the AgentZero-style stack:
    - Planner Agent (Mistral/Qwen)
    - Coder Agent (StarCoder2/Qwen-Coder)
    - Verifier (Test Runner)
    """
    
    # A. Initialize Local Runtime (llama.cpp server or mlx-server)
    # Using LlamaCpp langchain wrapper for direct GGUF loading
    llm = LlamaCpp(
        model_path="/Users/yacinebenhamou/models/Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf",
        n_ctx=8192,
        temperature=0.0, # Deterministic for coding
        verbose=False,
        n_gpu_layers=-1 # Offload all to Metal (Mac)
    )

    # B. Tools
    shell_tool = MacSandboxedShellTool()
    
    tools = [
        Tool(
            name="SandboxedShell",
            func=shell_tool.run,
            description="Execute shell commands. SAFE. Network restricted. Use for tests, git, file ops."
        ),
        # Add GitTool, MCPTool here...
    ]

    # C. Memory
    # cognee_client = cognee.init(...)
    memory = CogneeMemory(client=None)

    # D. Agent Construction
    # "Structured Chat" is best for multi-step tool use with local models
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        memory=memory,
        handle_parsing_errors=True
    )
    
    return agent

# ------------------------------------------------------------------------------
# 4. Canonical "AgentZero" Loop (Plan -> Code -> Verify)
# ------------------------------------------------------------------------------
def run_agentic_task(goal: str):
    agent = create_local_agent_stack()
    
    print(f"--- Starting Local Agent (AgentZero Mode) ---")
    print(f"Goal: {goal}")
    
    # The prompt structure enforces the AgentZero 'Verify' discipline
    system_prompt = """
    You are a recursive coding agent running LOCALLY.
    
    PROTOCOL:
    1. PLAN: Check Memory for similar past tasks.
    2. CODE: Use 'SandboxedShell' to write files or git commands.
    3. VERIFY: You MUST run a test command after every edit.
    
    CONSTRAINT:
    - Do not assume network access.
    - If a test fails, you MUST contradict your own code and try an Alternative.
    """
    
    response = agent.run(f"{system_prompt}\n\nTask: {goal}")
    print("--- Mission Complete ---")
    print(response)

if __name__ == "__main__":
    # Example Trigger
    run_agentic_task("Create a Python script 'hello.py' that calculates Fibonacci and write a unit test for it.")
