# VS Code Extension - Installation Guide

## Quick Install

1. **Open VS Code**
2. **Press** `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows/Linux)
3. **Type**: "Extensions: Install from VSIX..."
4. **Select**: `agenty-0.1.0.vsix` from this directory
5. **Reload** VS Code when prompted

## Manual Install (Development)

```bash
# From the vscode-extension directory
cd /Users/yacinebenhamou/AgentY/vscode-extension

# Install dependencies
npm install

# Compile TypeScript
npm run compile

# Open in VS Code
code .

# Press F5 to launch Extension Development Host
```

## Usage

### Starting AgentY

1. Click the **AgentY icon** (⚡) in the Activity Bar
2. Or run command: **"AgentY: Start Agent Session"**

### Submitting Tasks

1. In the AgentY sidebar, enter your goal in the input field
2. Click **"Build with Agents"** or press Enter
3. Watch the agents collaborate in real-time

### Features

- **Live Agent Feed** - See messages from Planner, Coder, Tester, Arbiter
- **Auto File Creation** - Generated code opens automatically in editor
- **Status Indicators** - Real-time agent status updates
- **WebSocket Streaming** - Live updates as agents work

## Configuration

Access settings via `Cmd+,` and search for "AgentY":

- **Orchestrator URL**: Default `http://127.0.0.1:8001`
- **LLM Model**: Default `qwen3:8b`
- **Require Approval**: Toggle plan approval flow

## Troubleshooting

### Extension Not Appearing

- Ensure you've reloaded VS Code after installation
- Check the Extensions view (`Cmd+Shift+X`) for "AgentY"

### Connection Errors

- Verify backend services are running:
  ```bash
  curl http://127.0.0.1:8001/agents
  ```
- Start services if needed:
  ```bash
  cd /Users/yacinebenhamou/AgentY
  ./start.sh
  ```

### No Generated Files

- Check workspace folder is open in VS Code
- Verify workspace permissions
- Check Output panel (View → Output → AgentY)

## Development

### Watch Mode

```bash
npm run watch
```

### Debugging

1. Open `vscode-extension` in VS Code
2. Press `F5` to launch Extension Development Host
3. Set breakpoints in TypeScript files
4. Test in the new window

### Building VSIX

```bash
npm install -g @vscode/vsce
vsce package
```

This creates `agenty-0.1.0.vsix` for distribution.
