/**
 * Monaco Code Editor Component
 * VS Code-style editor with syntax highlighting and live code display
 */

import { useEffect, useState } from 'react'
import Editor from '@monaco-editor/react'

interface CodeFile {
    name: string
    content: string
    language: string
}

interface CodeEditorProps {
    files: CodeFile[]
    activeFile?: string
    onFileSelect?: (fileName: string) => void
    onContentChange?: (fileName: string, content: string) => void
    readOnly?: boolean
}

function getLanguageFromFileName(fileName: string): string {
    const ext = fileName.split('.').pop()?.toLowerCase() || ''
    const languageMap: Record<string, string> = {
        'py': 'python',
        'js': 'javascript',
        'ts': 'typescript',
        'tsx': 'typescript',
        'jsx': 'javascript',
        'json': 'json',
        'md': 'markdown',
        'html': 'html',
        'css': 'css',
        'sh': 'shell',
        'bash': 'shell',
        'yml': 'yaml',
        'yaml': 'yaml',
        'sql': 'sql',
        'rs': 'rust',
        'go': 'go',
        'java': 'java',
        'cpp': 'cpp',
        'c': 'c',
        'rb': 'ruby',
    }
    return languageMap[ext] || 'plaintext'
}

export function CodeEditor({
    files,
    activeFile,
    onFileSelect,
    onContentChange,
    readOnly = true
}: CodeEditorProps) {
    const [selectedFile, setSelectedFile] = useState<string>(activeFile || files[0]?.name || '')

    useEffect(() => {
        if (activeFile && activeFile !== selectedFile) {
            setSelectedFile(activeFile)
        }
    }, [activeFile])

    const currentFile = files.find(f => f.name === selectedFile)

    const handleFileClick = (fileName: string) => {
        setSelectedFile(fileName)
        onFileSelect?.(fileName)
    }

    const handleEditorChange = (value: string | undefined) => {
        if (value !== undefined && currentFile) {
            onContentChange?.(currentFile.name, value)
        }
    }

    if (files.length === 0) {
        return (
            <div className="code-editor-empty">
                <div className="empty-icon">📝</div>
                <p>No files generated yet</p>
                <span>Agent-generated code will appear here</span>
            </div>
        )
    }

    return (
        <div className="code-editor-container">
            {/* File Tabs */}
            <div className="file-tabs">
                {files.map(file => (
                    <button
                        key={file.name}
                        className={`file-tab ${selectedFile === file.name ? 'active' : ''}`}
                        onClick={() => handleFileClick(file.name)}
                    >
                        <span className="file-icon">
                            {file.name.endsWith('.py') ? '🐍' :
                                file.name.endsWith('.js') || file.name.endsWith('.ts') ? '📜' :
                                    file.name.endsWith('.json') ? '📋' :
                                        file.name.endsWith('.md') ? '📝' : '📄'}
                        </span>
                        <span className="file-name">{file.name}</span>
                    </button>
                ))}
            </div>

            {/* Monaco Editor */}
            <div className="editor-wrapper">
                {currentFile && (
                    <Editor
                        height="100%"
                        language={getLanguageFromFileName(currentFile.name)}
                        value={currentFile.content}
                        onChange={handleEditorChange}
                        theme="vs-dark"
                        loading={
                            <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                height: '100%',
                                color: '#888',
                                background: '#1e1e2e'
                            }}>
                                Loading editor...
                            </div>
                        }
                        options={{
                            readOnly,
                            minimap: { enabled: true },
                            fontSize: 13,
                            fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
                            lineNumbers: 'on',
                            scrollBeyondLastLine: false,
                            wordWrap: 'on',
                            automaticLayout: true,
                            padding: { top: 12, bottom: 12 },
                            renderLineHighlight: 'all',
                            cursorBlinking: 'smooth',
                            smoothScrolling: true,
                        }}
                    />
                )}
            </div>
        </div>
    )
}

export default CodeEditor
