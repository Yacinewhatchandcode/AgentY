/**
 * AgentY VS Code Extension
 * Main extension entry point
 */

import * as vscode from 'vscode';
import { AgentYPanelProvider } from './AgentYPanelProvider';

export function activate(context: vscode.ExtensionContext) {
    console.log('AgentY extension is now active!');

    // Register the webview panel provider
    const provider = new AgentYPanelProvider(context.extensionUri);

    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('agenty.panel', provider)
    );

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('agenty.start', () => {
            provider.startSession();
            vscode.window.showInformationMessage('AgentY session started!');
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('agenty.stop', () => {
            provider.stopSession();
            vscode.window.showInformationMessage('AgentY session stopped.');
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('agenty.submitTask', async () => {
            const task = await vscode.window.showInputBox({
                prompt: 'Describe what you want to build',
                placeHolder: 'e.g., Create a REST API with Express'
            });

            if (task) {
                provider.submitTask(task);
            }
        })
    );
}

export function deactivate() {
    console.log('AgentY extension deactivated.');
}
