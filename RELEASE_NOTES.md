# AgentY - Release Notes

## Version 1.0.0 - Initial Release

**Release Date**: January 29, 2026

### 🎉 What's New

This is the first production release of **AgentY**, a fully local multi-agent AI coding system.

### ✨ Features

#### Multi-Agent System
- **4 Specialized Agents**: Planner, Coder, Tester, and Arbiter working in collaboration
- **Real-time Collaboration**: Agents communicate via MessageBus for coordinated workflows
- **Async Processing**: Non-blocking LLM calls for responsive operation

#### Code Execution
- **Real Terminal Execution**: Tester agent runs actual Python code in sandbox
- **Syntax Validation**: Automatic syntax checking before execution
- **Test Integration**: Automatic pytest execution for test files
- **Error Reporting**: Detailed stdout/stderr capture and display

#### Git Integration
- **Auto-Commit**: Successful builds automatically committed to Git
- **Meaningful Messages**: Semantic commit messages (feat:, fix:, etc.)
- **Version Control**: Full Git history of all agent-generated code

#### User Interface
- **Monaco Editor**: VS Code-style code editing with syntax highlighting
- **Plan Approval**: Review and modify plans before execution
- **Terminal Output**: Real-time display of code execution results
- **Agent Status**: Live status indicators for all agents
- **Session History**: Track and review past agent runs
- **Live Preview**: HTML/CSS/JS preview for web projects

#### VS Code Extension
- **Sidebar Integration**: AgentY panel in VS Code sidebar
- **WebSocket Streaming**: Real-time agent updates
- **Auto File Creation**: Generated files open automatically in editor
- **Command Palette**: Quick access to AgentY commands

#### Security
- **macOS Sandbox**: All code execution isolated via sandbox-exec
- **Workspace Isolation**: File operations restricted to workspace directory
- **Network Denial**: Sandboxed processes cannot access network
- **Local LLM**: All AI inference runs locally via Ollama

### 🛠 Technical Details

- **Backend**: Python 3.10+, FastAPI, Uvicorn, SQLite
- **Frontend**: React 18, TypeScript, Vite, Monaco Editor
- **LLM**: Ollama with qwen3:8b (or compatible models)
- **Extension**: TypeScript, VS Code API

### 📦 Installation

#### Full System
```bash
cd /Users/yacinebenhamou/AgentY
./start.sh
open http://localhost:5173
```

#### VS Code Extension
```bash
code --install-extension agenty-0.1.0.vsix
```

### 🐛 Known Issues

- Frontend may require manual restart after backend changes
- Large file generation (>1000 lines) may take longer
- Git operations require manual configuration on first use

### 🔮 Coming Soon

- Multi-language support (JavaScript, Go, Rust)
- Docker container generation
- Cloud deployment integration
- Team collaboration features
- Custom agent creation

### 📝 Documentation

- [README.md](README.md) - Complete setup guide
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Detailed overview
- [vscode-extension/INSTALL.md](vscode-extension/INSTALL.md) - Extension guide

### 🙏 Acknowledgments

Special thanks to:
- Ollama team for local LLM infrastructure
- Monaco Editor for VS Code integration
- FastAPI for modern Python web framework
- React team for UI framework

---

**Full Changelog**: Initial release

**Download**: `agenty-0.1.0.vsix` (56.15 KB)
