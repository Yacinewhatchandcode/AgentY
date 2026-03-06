# AgentY - Multi-Agent AI Coding System

<div align="center">

⚡ **A fully local, AgentZero-style coding assistant with true multi-agent architecture** ⚡

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey)

</div>

## 🚀 Features

### Multi-Agent Architecture
AgentY uses four specialized AI agents that collaborate in real-time:

| Agent | Role | Responsibilities |
|-------|------|------------------|
| 🧠 **Planner** | Strategy & Analysis | Breaks down goals into actionable steps, identifies files to create |
| 👨‍💻 **Coder** | Code Generation | Writes clean, working code based on plans |
| 🧪 **Tester** | Validation & Testing | Runs real code, validates syntax, executes tests |
| ⚖️ **Arbiter** | Coordination | Resolves conflicts, manages Git commits, orchestrates workflow |

### Key Capabilities

- **🔒 Secure Sandboxing** - All code execution uses macOS `sandbox-exec` for isolation
- **📝 Real Terminal Output** - See actual execution results, not just LLM analysis
- **🔀 Git Integration** - Auto-commit successful builds with meaningful messages
- **✅ User Approval Flow** - Optional plan review before code generation
- **📺 Monaco Editor** - VS Code-style editing with syntax highlighting
- **🔄 Real-time Streaming** - WebSocket-based live updates
- **💾 Persistent Memory** - SQLite-backed agent memory (Cognee-compatible)
- **🎨 Premium UI** - Dark theme with glassmorphism and micro-animations

## 📦 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│                    http://localhost:PORT                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Agent Feed  │  │   Monaco    │  │    Terminal View    │  │
│  │  (WebSocket)│  │   Editor    │  │   (Real Output)     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Orchestrator (FastAPI)                       │
│                  http://localhost:PORT                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Planner  │◄─┤ MessageBus├─►│  Coder   │◄─┤  Tester  │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│        │              │              │              │        │
│        └──────────────┴──────────────┴──────────────┘        │
│                          Arbiter                             │
└─────────────────────────────────────────────────────────────┘
              │                              │
              ▼                              ▼
┌──────────────────────┐        ┌──────────────────────┐
│    LLM (Ollama)      │        │   MCP Gateway        │
│ http://localhost:PORT│       │ http://localhost:PORT│
│                      │        │                      │
│  ┌────────────────┐  │        │  ┌──────────────┐   │
│  │   qwen3:8b     │  │        │  │ sandbox-exec │   │
│  │  (or others)   │  │        │  │  (Isolation) │   │
│  └────────────────┘  │        │  └──────────────┘   │
└──────────────────────┘        └──────────────────────┘
                                         │
                                         ▼
                                ┌──────────────────┐
                                │    Workspace     │
                                │  ./workspace/    │
                                │  (Git-tracked)   │
                                └──────────────────┘
```

## 🛠 Installation

### Prerequisites

- **macOS** (for `sandbox-exec` isolation)
- **Python 3.10+**
- **Node.js 18+**
- **Ollama** with a code model installed

### Setup

```bash
# Clone the repository
cd /Users/yacinebenhamou/AgentY

# Backend setup
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend setup
cd ../frontend
npm install

# Ensure Ollama is running with a model
ollama run qwen3:8b
```

## 🚀 Running AgentY

### Option 1: Full Stack (Recommended)

Start all services in separate terminals:

```bash
# Terminal 1: MCP Gateway (port 8000)
cd backend && source .venv/bin/activate
python mcp_gateway.py

# Terminal 2: Orchestrator (port 8001)
cd backend && source .venv/bin/activate
python orchestrator.py

# Terminal 3: Frontend (port 5173)
cd frontend
npm run dev
```

Then open **http://localhost:PORT** in your browser.

### Option 2: Quick Start Script

```bash
# Start everything with one command
./start.sh  # (if available)
```

## 💡 Usage

1. **Open the UI** at http://localhost:PORT
2. **Enter a goal** like "Create a REST API with Flask"
3. **Watch the agents collaborate**:
   - Planner creates a step-by-step plan
   - Coder writes the implementation
   - Tester validates and runs the code
   - Arbiter commits successful changes to Git
4. **View generated files** in the Monaco editor panel
5. **Check terminal output** for real execution results

## 🔧 Configuration

### LLM Model

By default, AgentY uses Ollama with `qwen3:8b`. To change the model:

```python
# In backend/agents.py, modify the BaseAgent constructor:
model: str = "your-preferred-model"
```

Available models:
- `qwen3:8b` (recommended for coding)
- `codellama:7b`
- `deepseek-coder:6.7b`
- Any Ollama-compatible model

### User Approval

Toggle "Require Approval" in the header to review plans before the Coder starts.

### Workspace

All generated files are saved to `./workspace/`. This directory is:
- Sandboxed for security
- Git-tracked for version control
- Isolated from your system files

## 🔌 VS Code Extension

A VS Code extension is included in `vscode-extension/`:

```bash
cd vscode-extension
npm install
npm run compile
```

Then load it as an unpacked extension in VS Code.

## 📁 Project Structure

```
AgentY/
├── backend/
│   ├── agents.py           # Multi-agent system (Planner, Coder, Tester, Arbiter)
│   ├── orchestrator.py     # FastAPI server with WebSocket streaming
│   ├── mcp_gateway.py      # Secure tool execution layer
│   ├── memory.py           # Persistent memory with SQLite
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx         # Main React component
│   │   ├── components/     # CodeEditor, PlanApproval, Terminal, AgentStatus
│   │   ├── hooks/          # useAgentStream WebSocket hook
│   │   └── index.css       # Complete design system
│   └── package.json
├── vscode-extension/
│   ├── src/
│   │   ├── extension.ts    # VS Code extension entry
│   │   └── AgentYPanelProvider.ts
│   └── package.json
├── workspace/              # Agent-generated files (sandboxed)
└── README.md
```

## 🔐 Security

AgentY uses multiple layers of security:

1. **macOS Sandbox** - All shell commands run in a restricted sandbox profile
2. **Workspace Isolation** - File operations limited to `./workspace/`
3. **Network Denial** - Sandboxed commands cannot access the network
4. **Local LLM** - All AI inference runs locally via Ollama

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - see LICENSE for details.

---

<div align="center">

https://github.com/user-attachments/assets/demo.mp4

**▶️ Watch the Demo**

</div>

---


<div align="center">
Built with ❤️ for local-first AI development
</div>


## 🇪🇺 EU AI Act Compliance

This project follows EU AI Act (Regulation 2024/1689) guidelines:

| Requirement | Status | Reference |
|-------------|--------|-----------|
| **Risk Classification** | ✅ Assessed | Art. 6 — Categorized as minimal/limited risk |
| **Transparency** | ✅ Documented | Art. 52 — AI use clearly disclosed |
| **Data Governance** | ✅ Implemented | Art. 10 — Data handling documented |
| **Human Oversight** | ✅ Enabled | Art. 14 — Human-in-the-loop available |
| **Bias Mitigation** | ✅ Addressed | Art. 10(2)(f) — Fairness considered |
| **Logging & Audit** | ✅ Active | Art. 12 — System activity logged |

### AI Transparency Statement

This project uses AI models for data processing and analysis. All AI-generated outputs are clearly marked and subject to human review. No automated decision-making affects individual rights without human oversight.

### Data & Privacy

- Personal data is processed in accordance with GDPR (Regulation 2016/679)
- Data minimization principles are applied
- Users can request data access, correction, or deletion
- No data is shared with third parties without explicit consent

> For questions about AI compliance, contact: compliance@prime-ai.fr
