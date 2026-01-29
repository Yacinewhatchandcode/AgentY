/**
 * AgentY - Multi-Agent AI Coding System
 * Full-featured UI with Monaco Editor, Plan Approval, and Real-time Streaming
 */

import { useState, useEffect, useCallback } from 'react'
import { useAgentStream } from './hooks/useAgentStream'
import { CodeEditor } from './components/CodeEditor'
import { PlanApproval } from './components/PlanApproval'
import { TerminalOutput } from './components/TerminalOutput'
import { AgentStatus } from './components/AgentStatus'
import SessionHistory from './components/SessionHistory'
import Terminal from './components/Terminal'
import Preview from './components/Preview'
import './index.css'

interface CodeFile {
    name: string
    content: string
    language: string
}

interface Plan {
    analysis: string
    steps: string[]
    files: { name: string; purpose: string }[]
    tests: string[]
}

interface Agent {
    name: string
    role: string
    status: 'idle' | 'thinking' | 'working' | 'waiting' | 'error'
    currentTask?: string
}

interface TerminalLine {
    type: 'stdout' | 'stderr' | 'command' | 'info'
    content: string
}

function App() {
    const { messages, status, startRun, cancelRun } = useAgentStream()
    const [goal, setGoal] = useState('')
    const [files, setFiles] = useState<CodeFile[]>([])
    const [currentPlan, setCurrentPlan] = useState<Plan | null>(null)
    const [awaitingApproval, setAwaitingApproval] = useState(false)
    const [terminalLines, setTerminalLines] = useState<TerminalLine[]>([])
    const [agents, setAgents] = useState<Agent[]>([
        { name: 'ProductManager', role: 'Specs & Requirements', status: 'idle' },
        { name: 'Planner', role: 'Strategy & Planning', status: 'idle' },
        { name: 'Architect', role: 'Design Patterns', status: 'idle' },
        { name: 'Coder', role: 'Code Generation', status: 'idle' },
        { name: 'Reviewer', role: 'Quality Gate', status: 'idle' },
        { name: 'Tester', role: 'Testing & Validation', status: 'idle' },
        { name: 'Debugger', role: 'Root Cause Analysis', status: 'idle' },
        { name: 'Executor', role: 'Launch & Preview', status: 'idle' },
        { name: 'Arbiter', role: 'Coordination', status: 'idle' }
    ])
    const [activeTab, setActiveTab] = useState<'activity' | 'terminal' | 'files' | 'history' | 'cli' | 'preview'>('activity')
    const [showApprovalRequired, setShowApprovalRequired] = useState(false)

    // Fetch agent status
    useEffect(() => {
        const fetchAgents = async () => {
            try {
                const res = await fetch('http://127.0.0.1:8001/agents')
                const data = await res.json()
                if (data.agents) {
                    setAgents(data.agents.map((a: any) => ({
                        name: a.name,
                        role: a.role,
                        status: a.is_running ? 'working' : 'idle',
                        currentTask: undefined
                    })))
                }
            } catch (e) {
                // Backend not available
            }
        }
        fetchAgents()
        const interval = setInterval(fetchAgents, 5000)
        return () => clearInterval(interval)
    }, [])

    // Process incoming messages
    useEffect(() => {
        if (messages.length === 0) return

        const lastMsg = messages[messages.length - 1]

        // Update agent statuses based on messages
        setAgents(prev => prev.map(agent => {
            const msgType = lastMsg.type?.toLowerCase()
            if (msgType === agent.name.toLowerCase()) {
                return {
                    ...agent,
                    status: 'working' as const,
                    currentTask: typeof lastMsg.content === 'string' ? lastMsg.content.slice(0, 50) : ''
                }
            }
            return agent
        }))

        // Extract plan if available
        if (lastMsg.metadata?.plan) {
            setCurrentPlan(lastMsg.metadata.plan as Plan)
            if (showApprovalRequired) {
                setAwaitingApproval(true)
            }
        }

        // Extract code files
        if (lastMsg.metadata?.code || lastMsg.metadata?.file) {
            const fileName = lastMsg.metadata.file as string || 'code.py'
            const code = lastMsg.metadata.code as string || ''

            setFiles(prev => {
                const existing = prev.find(f => f.name === fileName)
                if (existing) {
                    return prev.map(f => f.name === fileName ? { ...f, content: code } : f)
                }
                return [...prev, { name: fileName, content: code, language: 'python' }]
            })
        }

        // Extract terminal output
        if (lastMsg.metadata?.terminal || lastMsg.metadata?.output) {
            const rawOutput = lastMsg.metadata.terminal || lastMsg.metadata.output

            // Handle different output formats
            if (Array.isArray(rawOutput)) {
                // Array of terminal lines
                rawOutput.forEach((line: unknown) => {
                    if (typeof line === 'string') {
                        setTerminalLines(prev => [...prev, { type: 'stdout', content: line }])
                    } else if (line && typeof line === 'object' && 'content' in line) {
                        const lineObj = line as { type?: string; content: string }
                        setTerminalLines(prev => [...prev, {
                            type: (lineObj.type as 'stdout' | 'stderr' | 'command' | 'info') || 'stdout',
                            content: String(lineObj.content)
                        }])
                    }
                })
            } else if (typeof rawOutput === 'object' && rawOutput !== null) {
                // Single object with type/content
                const obj = rawOutput as { type?: string; content?: string }
                const content = obj.content || JSON.stringify(rawOutput)
                setTerminalLines(prev => [...prev, { type: 'stdout', content: String(content) }])
            } else if (typeof rawOutput === 'string') {
                // Simple string
                setTerminalLines(prev => [...prev, { type: 'stdout', content: rawOutput }])
            }
        }

    }, [messages, showApprovalRequired])

    const handleSubmit = useCallback(async (e: React.FormEvent) => {
        e.preventDefault()
        if (!goal.trim()) return

        // Reset state
        setFiles([])
        setCurrentPlan(null)
        setAwaitingApproval(false)
        setTerminalLines([{ type: 'info', content: `Starting task: ${goal}` }])

        // Update agent statuses
        setAgents(prev => prev.map(a => ({ ...a, status: 'waiting' as const })))

        await startRun(goal)
    }, [goal, startRun])

    const handlePlanApprove = () => {
        setAwaitingApproval(false)
        // Continue with execution (the backend continues automatically in current impl)
    }

    const handlePlanReject = (feedback: string) => {
        setAwaitingApproval(false)
        // In a full impl, this would send feedback to the Planner
        console.log('Plan rejected with feedback:', feedback)
    }

    const handlePlanModify = (modifiedPlan: Plan) => {
        setCurrentPlan(modifiedPlan)
        setAwaitingApproval(false)
        // In a full impl, this would send the modified plan to the Coder
    }

    const isWorking = status === 'running' || status === 'connecting'

    return (
        <div className="app">
            {/* Header */}
            <header className="header">
                <div className="logo">
                    <span className="logo-icon">⚡</span>
                    <span className="logo-text">AgentY</span>
                    <span className="logo-badge">Multi-Agent</span>
                </div>
                <nav className="nav">
                    <button
                        className={`nav-btn ${activeTab === 'activity' ? 'active' : ''}`}
                        onClick={() => setActiveTab('activity')}
                    >
                        Activity
                    </button>
                    <button
                        className={`nav-btn ${activeTab === 'files' ? 'active' : ''}`}
                        onClick={() => setActiveTab('files')}
                    >
                        Files ({files.length})
                    </button>
                    <button
                        className={`nav-btn ${activeTab === 'terminal' ? 'active' : ''}`}
                        onClick={() => setActiveTab('terminal')}
                    >
                        Output
                    </button>
                    <button
                        className={`nav-btn ${activeTab === 'cli' ? 'active' : ''}`}
                        onClick={() => setActiveTab('cli')}
                    >
                        🖥️ CLI
                    </button>
                    <button
                        className={`nav-btn ${activeTab === 'preview' ? 'active' : ''}`}
                        onClick={() => setActiveTab('preview')}
                    >
                        👁️ Preview
                    </button>
                    <button
                        className={`nav-btn ${activeTab === 'history' ? 'active' : ''}`}
                        onClick={() => setActiveTab('history')}
                    >
                        📜 History
                    </button>
                </nav>
                <div className="header-actions">
                    <button
                        className="download-btn"
                        onClick={async () => {
                            try {
                                const res = await fetch('http://127.0.0.1:8001/download-workspace')
                                if (res.ok) {
                                    const blob = await res.blob()
                                    const url = window.URL.createObjectURL(blob)
                                    const a = document.createElement('a')
                                    a.href = url
                                    a.download = `agenty-workspace-${Date.now()}.zip`
                                    a.click()
                                } else {
                                    alert('No files to download yet')
                                }
                            } catch {
                                alert('Download failed. Make sure backend is running.')
                            }
                        }}
                        title="Download workspace as ZIP"
                    >
                        📦 Download ZIP
                    </button>
                    <label className="approval-toggle">
                        <input
                            type="checkbox"
                            checked={showApprovalRequired}
                            onChange={(e) => setShowApprovalRequired(e.target.checked)}
                        />
                        <span>Require Approval</span>
                    </label>
                    <span className={`status-badge ${status}`}>
                        {status === 'idle' && '● Ready'}
                        {status === 'connecting' && '◌ Connecting'}
                        {status === 'running' && '◉ Running'}
                        {status === 'completed' && '✓ Complete'}
                        {status === 'error' && '✕ Error'}
                    </span>
                </div>
            </header>

            {/* Main Content */}
            <main className="main">
                {/* Left Panel - Agent Status + Activity */}
                <aside className="sidebar">
                    <AgentStatus agents={agents} />

                    <div className="activity-feed">
                        <h3>Activity Log</h3>
                        <div className="messages-list">
                            {messages.length === 0 ? (
                                <div className="empty-state">
                                    <p>No activity yet</p>
                                    <span>Submit a goal to start</span>
                                </div>
                            ) : (
                                messages.filter(m => m.type !== 'ping').map((msg, idx) => (
                                    <div key={idx} className={`message ${msg.type}`}>
                                        <span className="msg-sender">
                                            {msg.type === 'pm' && '📋'}
                                            {msg.type === 'productmanager' && '📋'}
                                            {msg.type === 'planner' && '🧠'}
                                            {msg.type === 'architect' && '🏗️'}
                                            {msg.type === 'coder' && '👨‍💻'}
                                            {msg.type === 'reviewer' && '👀'}
                                            {msg.type === 'tester' && '🧪'}
                                            {msg.type === 'debugger' && '🐛'}
                                            {msg.type === 'executor' && '🚀'}
                                            {msg.type === 'arbiter' && '⚖️'}
                                            {msg.type === 'system' && '⚡'}
                                            {msg.type === 'error' && '❌'}
                                        </span>
                                        <div className="msg-content">
                                            <span className="msg-type">{msg.type}</span>
                                            <p>{typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content)}</p>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </aside>

                {/* Center Panel - Dynamic Content */}
                <section className="content">
                    {/* Plan Approval Modal */}
                    {awaitingApproval && currentPlan && (
                        <div className="approval-overlay">
                            <PlanApproval
                                plan={currentPlan}
                                onApprove={handlePlanApprove}
                                onReject={handlePlanReject}
                                onModify={handlePlanModify}
                            />
                        </div>
                    )}

                    {/* Tab Content */}
                    {activeTab === 'activity' && (
                        <div className="welcome-content">
                            {!isWorking && messages.length === 0 ? (
                                <div className="welcome-screen">
                                    <h1>What would you like to build?</h1>
                                    <p>Describe your project and let the AI agents collaborate to build it.</p>
                                    <div className="feature-cards">
                                        <div className="feature-card">
                                            <span className="card-icon">🧠</span>
                                            <h4>Planner</h4>
                                            <p>Analyzes goals and creates detailed plans</p>
                                        </div>
                                        <div className="feature-card">
                                            <span className="card-icon">👨‍💻</span>
                                            <h4>Coder</h4>
                                            <p>Writes clean, working code</p>
                                        </div>
                                        <div className="feature-card">
                                            <span className="card-icon">🧪</span>
                                            <h4>Tester</h4>
                                            <p>Validates and runs tests</p>
                                        </div>
                                        <div className="feature-card">
                                            <span className="card-icon">⚖️</span>
                                            <h4>Arbiter</h4>
                                            <p>Coordinates and resolves conflicts</p>
                                        </div>
                                        <div className="feature-card">
                                            <span className="card-icon">🐛</span>
                                            <h4>Debugger</h4>
                                            <p>Analyzes failures and finds root causes</p>
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <div className="working-view">
                                    {currentPlan && !awaitingApproval && (
                                        <div className="plan-summary">
                                            <h3>📋 Current Plan</h3>
                                            <p>{currentPlan.analysis}</p>
                                            <div className="plan-stats">
                                                <span>{currentPlan.steps.length} steps</span>
                                                <span>{currentPlan.files.length} files</span>
                                                <span>{currentPlan.tests.length} tests</span>
                                            </div>
                                        </div>
                                    )}
                                    {files.length > 0 && (
                                        <div className="files-preview">
                                            <h3>📁 Generated Files</h3>
                                            <CodeEditor files={files} readOnly={true} />
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}

                    {activeTab === 'files' && (
                        <div className="files-content">
                            <CodeEditor
                                files={files}
                                readOnly={false}
                                onContentChange={(name, content) => {
                                    setFiles(prev => prev.map(f =>
                                        f.name === name ? { ...f, content } : f
                                    ))
                                }}
                            />
                        </div>
                    )}

                    {activeTab === 'terminal' && (
                        <div className="terminal-content">
                            <TerminalOutput
                                lines={terminalLines}
                                isRunning={isWorking}
                                title="Agent Terminal"
                            />
                        </div>
                    )}

                    {activeTab === 'cli' && (
                        <div className="cli-content">
                            <Terminal apiUrl="http://127.0.0.1:8001" />
                        </div>
                    )}

                    {activeTab === 'preview' && (
                        <div className="preview-content">
                            <Preview port={8080} />
                        </div>
                    )}

                    {activeTab === 'history' && (
                        <div className="history-content">
                            <SessionHistory
                                onLoadSession={(session) => {
                                    // Load messages from session
                                    console.log('Loading session:', session.session_id)
                                }}
                            />
                        </div>
                    )}
                </section>
            </main>

            {/* Input Bar */}
            <footer className="input-bar">
                <form onSubmit={handleSubmit}>
                    <input
                        type="text"
                        value={goal}
                        onChange={(e) => setGoal(e.target.value)}
                        placeholder="Describe what you want to build..."
                        disabled={isWorking}
                    />
                    <button type="submit" disabled={isWorking || !goal.trim()}>
                        {isWorking ? (
                            <>
                                <span className="spinner"></span>
                                Working...
                            </>
                        ) : (
                            <>
                                <span>⚡</span>
                                Build
                            </>
                        )}
                    </button>
                    {isWorking && (
                        <button type="button" className="cancel-btn" onClick={cancelRun}>
                            Cancel
                        </button>
                    )}
                </form>
            </footer>
        </div>
    )
}

export default App
