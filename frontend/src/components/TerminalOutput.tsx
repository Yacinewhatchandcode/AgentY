/**
 * Terminal Output Component
 * Displays real terminal output from agent code execution
 */

import { useEffect, useRef } from 'react'

interface TerminalLine {
    type: 'stdout' | 'stderr' | 'command' | 'info'
    content: string
    timestamp?: string
}

interface TerminalOutputProps {
    lines: TerminalLine[]
    isRunning?: boolean
    title?: string
}

export function TerminalOutput({ lines, isRunning = false, title = 'Terminal' }: TerminalOutputProps) {
    const terminalRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        // Auto-scroll to bottom on new output
        if (terminalRef.current) {
            terminalRef.current.scrollTop = terminalRef.current.scrollHeight
        }
    }, [lines])

    return (
        <div className="terminal-container">
            <div className="terminal-header">
                <div className="terminal-dots">
                    <span className="dot red"></span>
                    <span className="dot yellow"></span>
                    <span className="dot green"></span>
                </div>
                <span className="terminal-title">{title}</span>
                {isRunning && <span className="terminal-running">● Running</span>}
            </div>
            <div className="terminal-body" ref={terminalRef}>
                {lines.length === 0 ? (
                    <div className="terminal-empty">
                        <span className="prompt">$</span> Waiting for commands...
                    </div>
                ) : (
                    lines.map((line, index) => (
                        <div key={index} className={`terminal-line ${line.type}`}>
                            {line.type === 'command' && <span className="prompt">$</span>}
                            {line.type === 'info' && <span className="info-icon">ℹ</span>}
                            <span className="line-content">{line.content}</span>
                        </div>
                    ))
                )}
                {isRunning && (
                    <div className="terminal-cursor">
                        <span className="prompt">$</span>
                        <span className="cursor-blink">▊</span>
                    </div>
                )}
            </div>
        </div>
    )
}

export default TerminalOutput
