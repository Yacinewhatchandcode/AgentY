/**
 * Session History Component
 * Shows past agent runs with ability to restore/review
 */

import { useState, useEffect } from 'react'

interface Session {
    id: string
    goal: string
    timestamp: string
    status: 'completed' | 'failed' | 'running'
    filesGenerated: number
    duration?: string
}

interface SessionHistoryProps {
    onRestore?: (sessionId: string) => void
}

export function SessionHistory({ onRestore }: SessionHistoryProps) {
    const [sessions, setSessions] = useState<Session[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetchSessions()
    }, [])

    const fetchSessions = async () => {
        try {
            const response = await fetch('http://127.0.0.1:8001/sessions')
            if (response.ok) {
                const data = await response.json()
                setSessions(data.sessions || [])
            }
        } catch (e) {
            console.error('Failed to fetch sessions:', e)
        } finally {
            setLoading(false)
        }
    }

    const handleRestore = (sessionId: string) => {
        onRestore?.(sessionId)
    }

    if (loading) {
        return (
            <div className="session-history loading">
                <div className="spinner"></div>
                <p>Loading history...</p>
            </div>
        )
    }

    if (sessions.length === 0) {
        return (
            <div className="session-history empty">
                <span className="empty-icon">📜</span>
                <p>No previous sessions</p>
                <span>Your agent runs will appear here</span>
            </div>
        )
    }

    return (
        <div className="session-history">
            <h3>Session History</h3>
            <div className="sessions-list">
                {sessions.map((session) => (
                    <div key={session.id} className={`session-card ${session.status}`}>
                        <div className="session-header">
                            <span className="session-status">
                                {session.status === 'completed' && '✓'}
                                {session.status === 'failed' && '✗'}
                                {session.status === 'running' && '◉'}
                            </span>
                            <span className="session-time">
                                {new Date(session.timestamp).toLocaleString()}
                            </span>
                        </div>
                        <div className="session-goal">{session.goal}</div>
                        <div className="session-meta">
                            <span>{session.filesGenerated} files</span>
                            {session.duration && <span>{session.duration}</span>}
                        </div>
                        <button
                            className="restore-btn"
                            onClick={() => handleRestore(session.id)}
                        >
                            View Details
                        </button>
                    </div>
                ))}
            </div>
        </div>
    )
}

export default SessionHistory
