"""
AgentY Orchestrator v2 - Multi-Agent Edition
=============================================
Uses the true multi-agent system with Planner, Coder, Tester, and Arbiter.
"""

import asyncio
import json
import uuid
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

# Load environment variables from .env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[Config] Loaded environment from {env_path}")
except ImportError:
    print("[Config] python-dotenv not installed, using system environment")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from memory import get_memory
from agents import get_orchestrator, AgentMessage, MessageType
from session_history import get_session_manager

app = FastAPI(title="AgentY Orchestrator v2", version="2.0.0")

# CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active WebSocket connections per run
active_connections: Dict[str, List[WebSocket]] = {}

# Run state storage
runs: Dict[str, Dict[str, Any]] = {}

# Orchestrator instance
orchestrator = None
agents_started = False


class StartRequest(BaseModel):
    goal: str
    context: Optional[str] = None


class StartResponse(BaseModel):
    run_id: str
    status: str
    agents: List[str]


async def broadcast_to_run(run_id: str, message: Dict):
    """Send a message to all WebSocket clients watching this run."""
    if run_id in active_connections:
        message_json = json.dumps(message)
        for ws in active_connections[run_id]:
            try:
                await ws.send_text(message_json)
            except:
                pass


async def agent_message_handler(message: AgentMessage):
    """Handle messages from the multi-agent system and broadcast to WebSockets."""
    # Convert agent message to frontend format
    frontend_msg = {
        "type": message.sender.lower(),  # planner, coder, tester, arbiter
        "content": "",
        "timestamp": message.timestamp,
        "metadata": {}
    }
    
    # Format content based on message type
    if message.type == MessageType.STATUS:
        frontend_msg["content"] = message.content
    elif message.type == MessageType.PLAN:
        plan = message.content
        frontend_msg["content"] = f"Plan created: {len(plan.get('steps', []))} steps, {len(plan.get('files', []))} files"
        frontend_msg["metadata"] = {"plan": plan}
    elif message.type == MessageType.CODE:
        code_info = message.content
        frontend_msg["content"] = f"{'Revised' if code_info.get('revision') else 'Created'} {code_info.get('file')}"
        frontend_msg["metadata"] = {
            "file": code_info.get("file"),
            "code": code_info.get("code", "")[:2000]  # Truncate for WebSocket
        }
    elif message.type == MessageType.TEST_RESULT:
        result = message.content
        if result.get("passed"):
            frontend_msg["content"] = f"✓ {result.get('file')} passed"
        else:
            issues = result.get("issues", [])
            frontend_msg["content"] = f"✗ {result.get('file')} failed: {issues[0] if issues else 'unknown'}"
        frontend_msg["metadata"] = result
    elif message.type == MessageType.CONTRADICTION:
        frontend_msg["content"] = f"Issue found: {message.content.get('issues', ['unknown'])[0]}"
        frontend_msg["type"] = "arbiter"
    elif message.type == MessageType.RESOLUTION:
        frontend_msg["content"] = "Task completed"
        frontend_msg["type"] = "system"
    else:
        frontend_msg["content"] = str(message.content)[:200]
    
    # Store in memory
    memory = get_memory()
    run_id = message.content.get("run_id") if isinstance(message.content, dict) else None
    if run_id:
        memory.store(run_id, message.type.value, message.content)
    
    # Store in session history
    session_mgr = get_session_manager()
    for active_run_id in list(active_connections.keys()):
        try:
            session_mgr.add_message(
                session_id=active_run_id,
                agent=message.sender.lower(),
                message_type=frontend_msg["type"],
                content=frontend_msg["content"],
                metadata=frontend_msg.get("metadata", {})
            )
        except:
            pass
    
    # Broadcast to all active runs (simplified - in production, track run_id per message)
    for run_id in list(active_connections.keys()):
        await broadcast_to_run(run_id, frontend_msg)


@app.on_event("startup")
async def startup_event():
    """Initialize the multi-agent system on startup."""
    global orchestrator, agents_started
    
    orchestrator = get_orchestrator()
    orchestrator.add_message_listener(agent_message_handler)
    await orchestrator.start_agents()
    agents_started = True
    
    print("=" * 50)
    print("AgentY Multi-Agent System Started")
    print("=" * 50)
    print("Agents online:")
    for name in orchestrator.agents.keys():
        print(f"  ✓ {name}")
    print("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """Stop agents on shutdown."""
    global orchestrator
    if orchestrator:
        await orchestrator.stop_agents()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "multi_agent": True,
        "agents_online": list(orchestrator.agents.keys()) if orchestrator else [],
        "active_runs": len(runs)
    }


@app.get("/agents")
def list_agents():
    """List all agents and their status."""
    if not orchestrator:
        return {"error": "Orchestrator not initialized"}
    
    agents_info = []
    for name, agent in orchestrator.agents.items():
        agents_info.append({
            "name": name,
            "role": agent.role,
            "is_running": agent.is_running,
            "inbox_size": agent.inbox.qsize()
        })
    
    return {"agents": agents_info}


class TerminalRequest(BaseModel):
    command: str
    cwd: Optional[str] = None


@app.post("/terminal")
async def run_terminal_command(req: TerminalRequest):
    """Execute a terminal command in the workspace."""
    import subprocess
    
    workspace = Path("./workspace")
    workspace.mkdir(exist_ok=True)
    cwd = req.cwd or str(workspace)
    
    # Security: Block dangerous commands
    blocked = ['rm -rf /', 'sudo', 'chmod 777', 'mkfs', ':(){', 'dd if=']
    if any(b in req.command for b in blocked):
        return {"error": "Command blocked for safety", "output": "", "exit_code": 1}
    
    try:
        result = subprocess.run(
            req.command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60
        )
        return {
            "output": result.stdout or "",
            "error": result.stderr or "",
            "exit_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out (60s limit)", "output": "", "exit_code": 124}
    except Exception as e:
        return {"error": str(e), "output": "", "exit_code": 1}


@app.get("/download-workspace")
async def download_workspace():
    """Download the entire workspace as a ZIP file."""
    import zipfile
    import io
    from fastapi.responses import Response
    
    workspace = Path("./workspace")
    if not workspace.exists() or not any(workspace.iterdir()):
        return Response(content="No files in workspace", status_code=404)
    
    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in workspace.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(workspace)
                zf.write(file_path, arcname)
    
    zip_buffer.seek(0)
    
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=agenty-workspace-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
        }
    )


@app.post("/start", response_model=StartResponse)
async def start_run(req: StartRequest):
    """Start a new multi-agent run."""
    global orchestrator
    
    if not orchestrator or not agents_started:
        return StartResponse(
            run_id="error",
            status="Agents not started",
            agents=[]
        )
    
    run_id = f"run-{uuid.uuid4().hex[:8]}"
    
    runs[run_id] = {
        "goal": req.goal,
        "context": req.context,
        "status": "running",
        "started_at": datetime.now().isoformat()
    }
    
    # Create session in history
    session_mgr = get_session_manager()
    session_mgr.create_session(run_id, req.goal)
    
    # Run the task through multi-agent system
    context = {"run_id": run_id}
    if req.context:
        context["user_context"] = req.context
    
    asyncio.create_task(orchestrator.run_task(req.goal, context))
    
    return StartResponse(
        run_id=run_id,
        status="started",
        agents=list(orchestrator.agents.keys())
    )


@app.websocket("/stream/{run_id}")
async def stream_run(websocket: WebSocket, run_id: str):
    """WebSocket endpoint to stream multi-agent activity."""
    await websocket.accept()
    
    if run_id not in active_connections:
        active_connections[run_id] = []
    active_connections[run_id].append(websocket)
    
    try:
        # Send initial status with agent info
        await websocket.send_text(json.dumps({
            "type": "system",
            "content": f"Connected to multi-agent run {run_id}",
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "run": runs.get(run_id, {}),
                "agents": list(orchestrator.agents.keys()) if orchestrator else []
            }
        }))
        
        # Keep connection alive
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if data == "cancel":
                    runs[run_id]["status"] = "cancelled"
                    await websocket.send_text(json.dumps({
                        "type": "system",
                        "content": "Run cancelled by user",
                        "timestamp": datetime.now().isoformat()
                    }))
            except asyncio.TimeoutError:
                # Send ping
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        if run_id in active_connections:
            active_connections[run_id].remove(websocket)


@app.get("/runs")
def list_runs():
    """List all runs."""
    return {"runs": runs}


@app.get("/runs/{run_id}")
def get_run(run_id: str):
    """Get details of a specific run."""
    if run_id not in runs:
        return {"error": "Run not found"}
    
    memory = get_memory()
    history = memory.get_run_history(run_id)
    
    return {
        "run": runs[run_id],
        "history": history,
        "messages": orchestrator.get_message_history() if orchestrator else []
    }


@app.get("/messages")
def get_messages(limit: int = 50):
    """Get recent agent messages."""
    if not orchestrator:
        return {"messages": []}
    return {"messages": orchestrator.get_message_history(limit)}


@app.get("/graph/{run_id}")
def get_run_graph(run_id: str):
    """Get the memory graph for a run (for visualization)."""
    try:
        from graph_memory import get_graph_memory
        gm = get_graph_memory()
        graph = gm.get_run_graph(run_id)
        return graph
    except Exception as e:
        return {"error": str(e), "nodes": [], "edges": []}


@app.get("/agent/{agent_name}/history")
def get_agent_history(agent_name: str, run_id: Optional[str] = None):
    """Get decision history for a specific agent."""
    try:
        from graph_memory import get_graph_memory
        gm = get_graph_memory()
        history = gm.get_agent_history(agent_name, run_id)
        return {"agent": agent_name, "history": history}
    except Exception as e:
        return {"error": str(e), "history": []}


@app.get("/decisions/{node_id}/chain")
def get_decision_chain(node_id: str):
    """Get the chain of decisions leading to a node."""
    try:
        from graph_memory import get_graph_memory
        gm = get_graph_memory()
        chain = gm.get_decision_chain(node_id)
        return {"node_id": node_id, "chain": chain}
    except Exception as e:
        return {"error": str(e), "chain": []}


# ==================== SESSION HISTORY ENDPOINTS ====================

@app.get("/sessions")
def list_sessions(limit: int = 50, offset: int = 0, status: Optional[str] = None):
    """List past sessions with pagination."""
    session_mgr = get_session_manager()
    sessions = session_mgr.list_sessions(limit=limit, offset=offset, status=status)
    return {"sessions": sessions, "count": len(sessions)}


@app.get("/sessions/{session_id}")
def get_session(session_id: str, include_messages: bool = True):
    """Get a session by ID with full message history."""
    session_mgr = get_session_manager()
    session = session_mgr.get_session(session_id, include_messages=include_messages)
    if session:
        return session
    return {"error": "Session not found"}


@app.get("/sessions/{session_id}/summary")
def get_session_summary(session_id: str):
    """Get a summary of a session (agent activity, message types)."""
    session_mgr = get_session_manager()
    return session_mgr.get_session_summary(session_id)


@app.get("/sessions/search/{query}")
def search_sessions(query: str, limit: int = 20):
    """Search sessions by goal text."""
    session_mgr = get_session_manager()
    return {"results": session_mgr.search_sessions(query, limit)}


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    """Delete a session and its messages."""
    session_mgr = get_session_manager()
    session_mgr.delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}


@app.post("/sessions/{session_id}/complete")
def complete_session(session_id: str, summary: Optional[str] = None):
    """Mark a session as completed."""
    session_mgr = get_session_manager()
    session_mgr.update_session_status(session_id, "completed", summary=summary)
    return {"status": "completed", "session_id": session_id}


if __name__ == "__main__":
    import uvicorn
    print("Starting AgentY Multi-Agent Orchestrator on http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)


