"""
MCP Gateway - Secure Tool Execution Layer for AgentY
=====================================================
Exposes shell, git, and filesystem operations via HTTP.
Uses macOS sandbox-exec for isolation.
"""

import os
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="AgentY MCP Gateway", version="1.0.0")

# CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
WORKSPACE_DIR = Path(os.environ.get("AGENTY_WORKSPACE", "/Users/yacinebenhamou/AgentY/workspace"))
ALLOWED_TOOLS = {"shell", "git", "fs"}
TIMEOUT_SECONDS = 60

# macOS Sandbox Profile (deny network, restrict file access)
SANDBOX_PROFILE = """
(version 1)
(allow default)
(deny network*)
(allow file-read* (subpath "/usr"))
(allow file-read* (subpath "/bin"))
(allow file-read* (subpath "/Library"))
(allow file-read* (subpath "/System"))
(allow file-read* (subpath "{workspace}"))
(allow file-write* (subpath "{workspace}"))
"""


class InvokeRequest(BaseModel):
    tool: str
    action: str
    args: dict = {}


class InvokeResponse(BaseModel):
    success: bool
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    content: Optional[str] = None


def run_sandboxed_command(command: str, cwd: Path) -> tuple[int, str, str]:
    """Execute a command inside macOS sandbox."""
    # Create sandbox profile
    profile_content = SANDBOX_PROFILE.format(workspace=str(WORKSPACE_DIR))
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sb', delete=False) as f:
        f.write(profile_content)
        profile_path = f.name
    
    try:
        # Wrap command in sandbox-exec
        sandboxed_cmd = f"sandbox-exec -f {profile_path} /bin/zsh -c {shlex.quote(command)}"
        
        result = subprocess.run(
            sandboxed_cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(cwd),
            timeout=TIMEOUT_SECONDS,
            env={**os.environ, "HOME": str(WORKSPACE_DIR)}
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)
    finally:
        os.unlink(profile_path)


@app.get("/health")
def health():
    return {"status": "ok", "workspace": str(WORKSPACE_DIR)}


@app.post("/invoke", response_model=InvokeResponse)
def invoke(req: InvokeRequest):
    """Execute a tool action."""
    if req.tool not in ALLOWED_TOOLS:
        raise HTTPException(status_code=403, detail=f"Tool '{req.tool}' not allowed")
    
    # Ensure workspace exists
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    
    if req.tool == "shell":
        action = req.action
        args = req.args
        
        if action == "run":
            # Execute shell command in sandbox
            command = args.get("command", "echo 'No command'")
            exit_code, stdout, stderr = run_sandboxed_command(command, WORKSPACE_DIR)
            return InvokeResponse(
                success=(exit_code == 0),
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr
            )
        else:
            # Legacy: treat action as the command itself
            exit_code, stdout, stderr = run_sandboxed_command(action, WORKSPACE_DIR)
            return InvokeResponse(
                success=(exit_code == 0),
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr
            )
    
    elif req.tool == "git":
        action = req.action
        args = req.args
        
        if action == "init":
            git_cmd = "git init"
            exit_code, stdout, stderr = run_sandboxed_command(git_cmd, WORKSPACE_DIR)
            return InvokeResponse(
                success=(exit_code == 0),
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr
            )
        
        elif action == "add":
            path = args.get("path", ".")
            git_cmd = f"git add {shlex.quote(path)}"
            exit_code, stdout, stderr = run_sandboxed_command(git_cmd, WORKSPACE_DIR)
            return InvokeResponse(
                success=(exit_code == 0),
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr
            )
        
        elif action == "commit":
            message = args.get("message", "Auto-commit by AgentY")
            # Configure git if needed, then commit
            git_cmd = f'git config user.email "agent@agenty.local" 2>/dev/null; git config user.name "AgentY" 2>/dev/null; git commit -m {shlex.quote(message)}'
            exit_code, stdout, stderr = run_sandboxed_command(git_cmd, WORKSPACE_DIR)
            # Extract commit hash if successful
            commit_hash = None
            if exit_code == 0 and stdout:
                import re
                match = re.search(r'\[[\w\-/]+\s+([a-f0-9]+)\]', stdout)
                if match:
                    commit_hash = match.group(1)
            return InvokeResponse(
                success=(exit_code == 0),
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                content=commit_hash
            )
        
        elif action == "status":
            git_cmd = "git status --short"
            exit_code, stdout, stderr = run_sandboxed_command(git_cmd, WORKSPACE_DIR)
            return InvokeResponse(
                success=(exit_code == 0),
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr
            )
        
        elif action == "log":
            git_cmd = "git log --oneline -10"
            exit_code, stdout, stderr = run_sandboxed_command(git_cmd, WORKSPACE_DIR)
            return InvokeResponse(
                success=(exit_code == 0),
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr
            )
        
        else:
            # Fallback: run git with action as subcommand
            git_cmd = f"git {action}"
            exit_code, stdout, stderr = run_sandboxed_command(git_cmd, WORKSPACE_DIR)
            return InvokeResponse(
                success=(exit_code == 0),
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr
            )
    
    elif req.tool == "fs":
        action = req.action
        args = req.args
        
        if action == "read":
            file_path = WORKSPACE_DIR / args.get("path", "")
            if not file_path.is_relative_to(WORKSPACE_DIR):
                raise HTTPException(status_code=403, detail="Path outside workspace")
            if not file_path.exists():
                return InvokeResponse(success=False, stderr="File not found", content="")
            return InvokeResponse(success=True, content=file_path.read_text())
        
        elif action == "write":
            file_path = WORKSPACE_DIR / args.get("path", "")
            if not file_path.is_relative_to(WORKSPACE_DIR):
                raise HTTPException(status_code=403, detail="Path outside workspace")
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(args.get("content", ""))
            return InvokeResponse(success=True, stdout=f"Wrote {len(args.get('content', ''))} bytes")
        
        elif action == "list":
            dir_path = WORKSPACE_DIR / args.get("path", "")
            if not dir_path.is_relative_to(WORKSPACE_DIR):
                raise HTTPException(status_code=403, detail="Path outside workspace")
            if not dir_path.exists():
                return InvokeResponse(success=True, content="[]")
            files = [f.name for f in dir_path.iterdir()]
            return InvokeResponse(success=True, content=str(files))
        
        elif action == "delete":
            file_path = WORKSPACE_DIR / args.get("path", "")
            if not file_path.is_relative_to(WORKSPACE_DIR):
                raise HTTPException(status_code=403, detail="Path outside workspace")
            if file_path.exists():
                file_path.unlink()
            return InvokeResponse(success=True, stdout="Deleted")
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown fs action: {action}")
    
    raise HTTPException(status_code=400, detail="Unknown tool")


if __name__ == "__main__":
    import uvicorn
    print(f"Starting MCP Gateway on http://127.0.0.1:8000")
    print(f"Workspace: {WORKSPACE_DIR}")
    uvicorn.run(app, host="127.0.0.1", port=8000)
