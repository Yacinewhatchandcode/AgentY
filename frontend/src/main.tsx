import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

// Error Boundary Component
class ErrorBoundary extends React.Component<
    { children: React.ReactNode },
    { hasError: boolean; error: Error | null }
> {
    constructor(props: { children: React.ReactNode }) {
        super(props)
        this.state = { hasError: false, error: null }
    }

    static getDerivedStateFromError(error: Error) {
        return { hasError: true, error }
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        console.error('React Error:', error, errorInfo)
    }

    render() {
        if (this.state.hasError) {
            return (
                <div style={{
                    padding: '40px',
                    background: '#1a1a2e',
                    color: '#ff6b6b',
                    minHeight: '100vh',
                    fontFamily: 'monospace'
                }}>
                    <h1 style={{ color: '#f0f0f5' }}>⚠️ Something went wrong</h1>
                    <pre style={{
                        background: '#0a0a0f',
                        padding: '20px',
                        borderRadius: '8px',
                        overflow: 'auto',
                        marginTop: '20px'
                    }}>
                        {this.state.error?.message}
                        {'\n\n'}
                        {this.state.error?.stack}
                    </pre>
                    <button
                        onClick={() => window.location.reload()}
                        style={{
                            marginTop: '20px',
                            padding: '12px 24px',
                            background: '#6366f1',
                            border: 'none',
                            borderRadius: '8px',
                            color: 'white',
                            cursor: 'pointer',
                            fontSize: '14px'
                        }}
                    >
                        🔄 Reload App
                    </button>
                </div>
            )
        }

        return this.props.children
    }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
        <ErrorBoundary>
            <App />
        </ErrorBoundary>
    </React.StrictMode>,
)
