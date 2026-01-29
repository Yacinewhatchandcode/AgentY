/**
 * Agent Status Component
 * Shows real-time status of all agents in the system
 */

interface Agent {
    name: string
    role: string
    status: 'idle' | 'thinking' | 'working' | 'waiting' | 'error'
    currentTask?: string
}

interface AgentStatusProps {
    agents: Agent[]
}

const agentEmojis: Record<string, string> = {
    'Planner': '🧠',
    'Coder': '👨‍💻',
    'Tester': '🧪',
    'Arbiter': '⚖️'
}

const statusColors: Record<string, string> = {
    'idle': '#6b7280',
    'thinking': '#f59e0b',
    'working': '#10b981',
    'waiting': '#3b82f6',
    'error': '#ef4444'
}

export function AgentStatus({ agents }: AgentStatusProps) {
    return (
        <div className="agent-status-panel">
            <h3 className="status-title">Agent Status</h3>
            <div className="agents-grid">
                {agents.map(agent => (
                    <div key={agent.name} className={`agent-card ${agent.status}`}>
                        <div className="agent-header">
                            <span className="agent-emoji">{agentEmojis[agent.name] || '🤖'}</span>
                            <div className="agent-info">
                                <span className="agent-name">{agent.name}</span>
                                <span className="agent-role">{agent.role}</span>
                            </div>
                            <div
                                className="status-indicator"
                                style={{ backgroundColor: statusColors[agent.status] }}
                                title={agent.status}
                            >
                                {agent.status === 'thinking' && (
                                    <span className="thinking-dots">
                                        <span>.</span><span>.</span><span>.</span>
                                    </span>
                                )}
                                {agent.status === 'working' && (
                                    <span className="working-spinner">⟳</span>
                                )}
                            </div>
                        </div>
                        {agent.currentTask && (
                            <div className="agent-task">
                                <span className="task-label">Current:</span>
                                <span className="task-text">{agent.currentTask}</span>
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    )
}

export default AgentStatus
