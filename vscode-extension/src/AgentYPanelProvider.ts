/**
 * AgentY Panel Provider
 * Provides the webview panel for the AgentY sidebar
 */

import * as vscode from 'vscode';

interface AgentMessage {
    type: string;
    content: string;
    timestamp: string;
    metadata?: Record<string, unknown>;
}

export class AgentYPanelProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'agenty.panel';

    private _view?: vscode.WebviewView;
    private _ws?: WebSocket;
    private _messages: AgentMessage[] = [];
    private _status: 'idle' | 'connecting' | 'running' | 'completed' | 'error' = 'idle';

    constructor(private readonly _extensionUri: vscode.Uri) { }

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        _context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ) {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };

        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

        // Handle messages from the webview
        webviewView.webview.onDidReceiveMessage(async (message) => {
            switch (message.command) {
                case 'submitTask':
                    this.submitTask(message.task);
                    break;
                case 'cancelTask':
                    this.stopSession();
                    break;
            }
        });
    }

    public startSession() {
        this._status = 'idle';
        this._messages = [];
        this._updateWebview();
    }

    public stopSession() {
        if (this._ws) {
            this._ws.close();
            this._ws = undefined;
        }
        this._status = 'idle';
        this._updateWebview();
    }

    public async submitTask(task: string) {
        const config = vscode.workspace.getConfiguration('agenty');
        const orchestratorUrl = config.get<string>('orchestratorUrl', 'http://127.0.0.1:8001');

        try {
            this._status = 'connecting';
            this._messages = [];
            this._updateWebview();

            // Start the task
            const response = await fetch(`${orchestratorUrl}/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ goal: task })
            });

            if (!response.ok) {
                throw new Error('Failed to start task');
            }

            const data = await response.json() as { run_id: string };
            const runId = data.run_id;

            // Connect to WebSocket for streaming
            const wsUrl = orchestratorUrl.replace('http', 'ws');
            this._ws = new WebSocket(`${wsUrl}/stream/${runId}`);

            this._ws.onopen = () => {
                this._status = 'running';
                this._messages.push({
                    type: 'system',
                    content: `Connected to run ${runId}`,
                    timestamp: new Date().toISOString()
                });
                this._updateWebview();
            };

            this._ws.onmessage = (event: MessageEvent) => {
                try {
                    const msg = JSON.parse(event.data);
                    this._messages.push(msg);
                    this._updateWebview();

                    // If code was generated, optionally open it in editor
                    if (msg.metadata?.file && msg.metadata?.code) {
                        this._showGeneratedCode(
                            msg.metadata.file as string,
                            msg.metadata.code as string
                        );
                    }
                } catch (e) {
                    console.error('Failed to parse message:', e);
                }
            };

            this._ws.onclose = () => {
                this._status = 'completed';
                this._updateWebview();
            };

            this._ws.onerror = () => {
                this._status = 'error';
                this._messages.push({
                    type: 'error',
                    content: 'WebSocket connection error',
                    timestamp: new Date().toISOString()
                });
                this._updateWebview();
            };

        } catch (error) {
            this._status = 'error';
            this._messages.push({
                type: 'error',
                content: `Error: ${error}`,
                timestamp: new Date().toISOString()
            });
            this._updateWebview();
        }
    }

    private async _showGeneratedCode(fileName: string, code: string) {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders || workspaceFolders.length === 0) {
            return;
        }

        const filePath = vscode.Uri.joinPath(workspaceFolders[0].uri, fileName);

        try {
            await vscode.workspace.fs.writeFile(filePath, Buffer.from(code, 'utf8'));
            const doc = await vscode.workspace.openTextDocument(filePath);
            await vscode.window.showTextDocument(doc, { preview: false });
        } catch (e) {
            console.error('Failed to show generated code:', e);
        }
    }

    private _updateWebview() {
        if (this._view) {
            this._view.webview.postMessage({
                command: 'update',
                status: this._status,
                messages: this._messages
            });
        }
    }

    private _getHtmlForWebview(webview: vscode.Webview): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AgentY</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: var(--vscode-font-family);
            font-size: var(--vscode-font-size);
            color: var(--vscode-foreground);
            background: var(--vscode-sideBar-background);
            padding: 12px;
        }
        
        .header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 16px;
        }
        
        .logo {
            font-size: 20px;
        }
        
        .title {
            font-weight: 600;
            font-size: 14px;
        }
        
        .status {
            margin-left: auto;
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 10px;
            background: var(--vscode-badge-background);
            color: var(--vscode-badge-foreground);
        }
        
        .status.running {
            background: #10b981;
            color: white;
        }
        
        .status.error {
            background: #ef4444;
            color: white;
        }
        
        .input-section {
            margin-bottom: 16px;
        }
        
        .input-section input {
            width: 100%;
            padding: 8px 12px;
            background: var(--vscode-input-background);
            border: 1px solid var(--vscode-input-border);
            border-radius: 4px;
            color: var(--vscode-input-foreground);
            font-size: 13px;
        }
        
        .input-section input:focus {
            outline: none;
            border-color: var(--vscode-focusBorder);
        }
        
        .input-section button {
            margin-top: 8px;
            width: 100%;
            padding: 8px;
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
        }
        
        .input-section button:hover {
            background: var(--vscode-button-hoverBackground);
        }
        
        .messages {
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .message {
            padding: 8px 10px;
            background: var(--vscode-editor-background);
            border-radius: 4px;
            font-size: 12px;
            border-left: 3px solid var(--vscode-textLink-foreground);
        }
        
        .message.planner { border-left-color: #f59e0b; }
        .message.coder { border-left-color: #10b981; }
        .message.tester { border-left-color: #3b82f6; }
        .message.arbiter { border-left-color: #8b5cf6; }
        .message.error { border-left-color: #ef4444; }
        
        .msg-type {
            font-weight: 600;
            text-transform: uppercase;
            font-size: 10px;
            color: var(--vscode-descriptionForeground);
            margin-bottom: 4px;
        }
        
        .empty {
            text-align: center;
            padding: 32px;
            color: var(--vscode-descriptionForeground);
        }
    </style>
</head>
<body>
    <div class="header">
        <span class="logo">⚡</span>
        <span class="title">AgentY</span>
        <span class="status" id="status">Ready</span>
    </div>
    
    <div class="input-section">
        <input type="text" id="taskInput" placeholder="Describe what you want to build..." />
        <button id="submitBtn">Build with Agents</button>
    </div>
    
    <div class="messages" id="messages">
        <div class="empty">
            <p>Submit a task to start building</p>
        </div>
    </div>
    
    <script>
        const vscode = acquireVsCodeApi();
        const taskInput = document.getElementById('taskInput');
        const submitBtn = document.getElementById('submitBtn');
        const messagesEl = document.getElementById('messages');
        const statusEl = document.getElementById('status');
        
        submitBtn.addEventListener('click', () => {
            const task = taskInput.value.trim();
            if (task) {
                vscode.postMessage({ command: 'submitTask', task });
                taskInput.value = '';
            }
        });
        
        taskInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                submitBtn.click();
            }
        });
        
        window.addEventListener('message', (event) => {
            const message = event.data;
            
            if (message.command === 'update') {
                // Update status
                statusEl.textContent = message.status;
                statusEl.className = 'status ' + message.status;
                
                // Update messages
                if (message.messages.length === 0) {
                    messagesEl.innerHTML = '<div class="empty"><p>Submit a task to start building</p></div>';
                } else {
                    messagesEl.innerHTML = message.messages.map(msg => 
                        '<div class="message ' + msg.type + '">' +
                            '<div class="msg-type">' + msg.type + '</div>' +
                            '<div class="msg-content">' + 
                                (typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content)) +
                            '</div>' +
                        '</div>'
                    ).join('');
                    messagesEl.scrollTop = messagesEl.scrollHeight;
                }
            }
        });
    </script>
</body>
</html>`;
    }
}
