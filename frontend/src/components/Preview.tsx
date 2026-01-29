/**
 * Preview Component
 * Live preview for web projects (HTML/CSS/JS)
 */

import { useEffect, useRef } from 'react'

interface PreviewProps {
    html?: string
    css?: string
    javascript?: string
}

export function Preview({ html = '', css = '', javascript = '' }: PreviewProps) {
    const iframeRef = useRef<HTMLIFrameElement>(null)

    useEffect(() => {
        if (!iframeRef.current) return

        const document = iframeRef.current.contentDocument
        if (!document) return

        const content = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {
      margin: 0;
      padding: 16px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    ${css}
  </style>
</head>
<body>
  ${html}
  <script>
    try {
      ${javascript}
    } catch (e) {
      console.error('Preview error:', e);
      document.body.innerHTML += '<div style="color: red; padding: 20px; border: 2px solid red; margin: 20px;">Error: ' + e.message + '</div>';
    }
  </script>
</body>
</html>
    `

        document.open()
        document.write(content)
        document.close()
    }, [html, css, javascript])

    if (!html && !css && !javascript) {
        return (
            <div className="preview-empty">
                <span className="preview-icon">👁️</span>
                <p>No preview available</p>
                <span>Generate HTML/CSS/JS to see a live preview</span>
            </div>
        )
    }

    return (
        <div className="preview-container">
            <div className="preview-header">
                <span className="preview-title">Live Preview</span>
                <button
                    className="preview-refresh"
                    onClick={() => {
                        if (iframeRef.current) {
                            iframeRef.current.src = iframeRef.current.src
                        }
                    }}
                >
                    ↻ Refresh
                </button>
            </div>
            <iframe
                ref={iframeRef}
                className="preview-iframe"
                title="Preview"
                sandbox="allow-scripts"
            />
        </div>
    )
}

export default Preview
