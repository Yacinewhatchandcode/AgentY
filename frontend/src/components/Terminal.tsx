import { useState, useRef, useEffect } from 'react'
import './Terminal.css'

interface TerminalLine {
    type: 'input' | 'output' | 'error' | 'system'
    content: string
    timestamp: string
}

interface TerminalProps {
    apiUrl?: string
    initialCommand?: string
}

export default function Terminal({ apiUrl = 'http://127.0.0.1:8001', initialCommand }: TerminalProps) {
    const [lines, setLines] = useState<TerminalLine[]>([
        { type: 'system', content: '🖥️ AgentY Terminal - Type commands or "help" for options', timestamp: new Date().toISOString() }
    ])
    const [input, setInput] = useState('')
    const [isRunning, setIsRunning] = useState(false)
    const [history, setHistory] = useState<string[]>([])
    const [historyIndex, setHistoryIndex] = useState(-1)
    const terminalRef = useRef<HTMLDivElement>(null)
    const inputRef = useRef<HTMLInputElement>(null)

    useEffect(() => {
        if (terminalRef.current) {
            terminalRef.current.scrollTop = terminalRef.current.scrollHeight
        }
    }, [lines])

    useEffect(() => {
        if (initialCommand) {
            executeCommand(initialCommand)
        }
    }, [initialCommand])

    const addLine = (type: TerminalLine['type'], content: string) => {
        setLines(prev => [...prev, {
            type,
            content,
            timestamp: new Date().toISOString()
        }])
    }

    const executeCommand = async (cmd: string) => {
        if (!cmd.trim()) return

        addLine('input', `$ ${cmd}`)
        setHistory(prev => [...prev, cmd])
        setHistoryIndex(-1)
        setInput('')
        setIsRunning(true)

        // Handle built-in commands
        if (cmd === 'help') {
            addLine('system', `
Available commands:
  help          - Show this help
  clear         - Clear terminal
  ls            - List workspace files
  cat <file>    - Show file contents
  run <file>    - Execute a Python file
  test <file>   - Run tests on file
  preview       - Start preview server
  download      - Download workspace as ZIP
  agents        - Show agent status
            `.trim())
            setIsRunning(false)
            return
        }

        if (cmd === 'clear') {
            setLines([{ type: 'system', content: '🖥️ Terminal cleared', timestamp: new Date().toISOString() }])
            setIsRunning(false)
            return
        }

        if (cmd === 'agents') {
            try {
                const res = await fetch(`${apiUrl}/agents`)
                const data = await res.json()
                const status = data.agents.map((a: { name: string; is_running: boolean }) =>
                    `  ${a.is_running ? '✓' : '✗'} ${a.name}`
                ).join('\n')
                addLine('output', `Agent Status:\n${status}`)
            } catch (e) {
                addLine('error', `Error: ${e}`)
            }
            setIsRunning(false)
            return
        }

        if (cmd === 'download') {
            try {
                const res = await fetch(`${apiUrl}/download-workspace`)
                if (res.ok) {
                    const blob = await res.blob()
                    const url = window.URL.createObjectURL(blob)
                    const a = document.createElement('a')
                    a.href = url
                    a.download = `agenty-workspace-${Date.now()}.zip`
                    a.click()
                    addLine('system', '📦 Download started!')
                } else {
                    addLine('error', 'Download endpoint not available')
                }
            } catch (e) {
                addLine('error', `Download failed: ${e}`)
            }
            setIsRunning(false)
            return
        }

        // Send command to backend
        try {
            const res = await fetch(`${apiUrl}/terminal`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: cmd })
            })

            if (!res.ok) {
                // If terminal endpoint doesn't exist, show message
                addLine('error', 'Terminal endpoint not available. Run command locally.')
                setIsRunning(false)
                return
            }

            const data = await res.json()

            if (data.output) {
                addLine('output', data.output)
            }
            if (data.error) {
                addLine('error', data.error)
            }
            if (data.exit_code !== undefined && data.exit_code !== 0) {
                addLine('system', `Exit code: ${data.exit_code}`)
            }
        } catch (e) {
            addLine('error', `Connection error: ${e}`)
        }

        setIsRunning(false)
    }

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !isRunning) {
            executeCommand(input)
        } else if (e.key === 'ArrowUp') {
            e.preventDefault()
            if (history.length > 0) {
                const newIndex = historyIndex < history.length - 1 ? historyIndex + 1 : historyIndex
                setHistoryIndex(newIndex)
                setInput(history[history.length - 1 - newIndex] || '')
            }
        } else if (e.key === 'ArrowDown') {
            e.preventDefault()
            if (historyIndex > 0) {
                const newIndex = historyIndex - 1
                setHistoryIndex(newIndex)
                setInput(history[history.length - 1 - newIndex] || '')
            } else {
                setHistoryIndex(-1)
                setInput('')
            }
        }
    }

    return (
        <div className="terminal-container">
            <div className="terminal-header">
                <div className="terminal-dots">
                    <span className="dot red"></span>
                    <span className="dot yellow"></span>
                    <span className="dot green"></span>
                </div>
                <span className="terminal-title">Terminal</span>
                <button className="terminal-clear" onClick={() => setLines([])}>Clear</button>
            </div>
            <div className="terminal-body" ref={terminalRef} onClick={() => inputRef.current?.focus()}>
                {lines.map((line, i) => (
                    <div key={i} className={`terminal-line ${line.type}`}>
                        <pre>{line.content}</pre>
                    </div>
                ))}
                <div className="terminal-input-line">
                    <span className="prompt">$</span>
                    <input
                        ref={inputRef}
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={isRunning}
                        placeholder={isRunning ? 'Running...' : 'Enter command...'}
                        autoFocus
                    />
                </div>
            </div>
        </div>
    )
}
