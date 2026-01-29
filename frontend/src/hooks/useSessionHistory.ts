import { useState, useEffect, useCallback } from 'react'

interface Session {
    session_id: string
    goal: string
    status: string
    started_at: string
    ended_at?: string
    summary?: string
    message_count?: number
}

interface SessionMessage {
    id: number
    session_id: string
    agent: string
    message_type: string
    content: string
    timestamp: string
    metadata?: Record<string, unknown>
}

interface SessionDetail extends Session {
    messages: SessionMessage[]
}

export function useSessionHistory() {
    const [sessions, setSessions] = useState<Session[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [selectedSession, setSelectedSession] = useState<SessionDetail | null>(null)

    const fetchSessions = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const res = await fetch('http://127.0.0.1:8001/sessions')
            const data = await res.json()
            setSessions(data.sessions || [])
        } catch (e) {
            setError('Failed to fetch sessions')
        } finally {
            setLoading(false)
        }
    }, [])

    const fetchSession = useCallback(async (sessionId: string) => {
        setLoading(true)
        setError(null)
        try {
            const res = await fetch(`http://127.0.0.1:8001/sessions/${sessionId}`)
            const data = await res.json()
            if (data.error) {
                setError(data.error)
                setSelectedSession(null)
            } else {
                setSelectedSession(data)
            }
        } catch (e) {
            setError('Failed to fetch session details')
            setSelectedSession(null)
        } finally {
            setLoading(false)
        }
    }, [])

    const deleteSession = useCallback(async (sessionId: string) => {
        try {
            await fetch(`http://127.0.0.1:8001/sessions/${sessionId}`, {
                method: 'DELETE'
            })
            setSessions(prev => prev.filter(s => s.session_id !== sessionId))
            if (selectedSession?.session_id === sessionId) {
                setSelectedSession(null)
            }
        } catch (e) {
            setError('Failed to delete session')
        }
    }, [selectedSession])

    const searchSessions = useCallback(async (query: string) => {
        if (!query.trim()) {
            return fetchSessions()
        }
        setLoading(true)
        try {
            const res = await fetch(`http://127.0.0.1:8001/sessions/search/${encodeURIComponent(query)}`)
            const data = await res.json()
            setSessions(data.results || [])
        } catch (e) {
            setError('Search failed')
        } finally {
            setLoading(false)
        }
    }, [fetchSessions])

    useEffect(() => {
        fetchSessions()
    }, [fetchSessions])

    return {
        sessions,
        loading,
        error,
        selectedSession,
        fetchSessions,
        fetchSession,
        deleteSession,
        searchSessions,
        clearSelection: () => setSelectedSession(null)
    }
}

export type { Session, SessionMessage, SessionDetail }
