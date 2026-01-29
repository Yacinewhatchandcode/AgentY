import { useState, useEffect, useCallback, useRef } from 'react'

interface AgentMessage {
    type: 'pm' | 'productmanager' | 'planner' | 'architect' | 'coder' | 'reviewer' | 'tester' | 'debugger' | 'executor' | 'arbiter' | 'system' | 'error' | 'terminal' | 'ping'
    content: string
    timestamp: string
    metadata?: Record<string, unknown>
}

interface UseAgentStreamResult {
    messages: AgentMessage[]
    status: 'idle' | 'connecting' | 'running' | 'completed' | 'error'
    runId: string | null
    startRun: (goal: string) => Promise<void>
    cancelRun: () => void
}

export function useAgentStream(): UseAgentStreamResult {
    const [messages, setMessages] = useState<AgentMessage[]>([])
    const [status, setStatus] = useState<UseAgentStreamResult['status']>('idle')
    const [runId, setRunId] = useState<string | null>(null)
    const wsRef = useRef<WebSocket | null>(null)

    const startRun = useCallback(async (goal: string) => {
        try {
            setStatus('connecting')
            setMessages([])

            // Start the run via HTTP
            const response = await fetch('http://127.0.0.1:8001/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ goal })
            })

            if (!response.ok) {
                throw new Error('Failed to start run')
            }

            const data = await response.json()
            const newRunId = data.run_id
            setRunId(newRunId)

            // Connect to WebSocket for streaming
            const ws = new WebSocket(`ws://127.0.0.1:8001/stream/${newRunId}`)
            wsRef.current = ws

            ws.onopen = () => {
                setStatus('running')
            }

            ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data) as AgentMessage

                    // Ignore ping messages
                    if (message.type === 'ping') return

                    // Check for completion
                    if (message.type === 'system' && message.content.includes('complete')) {
                        setStatus('completed')
                    }

                    setMessages((prev) => [...prev, message])
                } catch (e) {
                    console.error('Failed to parse message:', e)
                }
            }

            ws.onerror = () => {
                setStatus('error')
            }

            ws.onclose = () => {
                if (status === 'running') {
                    setStatus('completed')
                }
            }

        } catch (error) {
            console.error('Failed to start run:', error)
            setStatus('error')
            setMessages((prev) => [...prev, {
                type: 'error',
                content: `Failed to start: ${error}`,
                timestamp: new Date().toISOString()
            }])
        }
    }, [status])

    const cancelRun = useCallback(() => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send('cancel')
        }
        setStatus('idle')
    }, [])

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (wsRef.current) {
                wsRef.current.close()
            }
        }
    }, [])

    return { messages, status, runId, startRun, cancelRun }
}
