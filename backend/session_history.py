"""
Session History Backend
Tracks and stores agent run sessions for history/replay
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

DB_PATH = Path(__file__).parent / "sessions.db"


class SessionHistory:
    """Manages session history storage and retrieval."""
    
    def __init__(self):
        self._init_db()
    
    def _init_db(self):
        """Initialize the sessions database."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                goal TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                files_generated INTEGER DEFAULT 0,
                duration_seconds INTEGER,
                messages TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                content TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_session(self, run_id: str, goal: str) -> Dict:
        """Create a new session record."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO sessions (id, goal, timestamp, status)
            VALUES (?, ?, ?, ?)
        """, (run_id, goal, timestamp, 'running'))
        
        conn.commit()
        conn.close()
        
        return {
            "id": run_id,
            "goal": goal,
            "timestamp": timestamp,
            "status": "running"
        }
    
    def update_session(
        self,
        run_id: str,
        status: Optional[str] = None,
        files_generated: Optional[int] = None,
        duration_seconds: Optional[int] = None,
        messages: Optional[List[Dict]] = None
    ):
        """Update session details."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if status:
            updates.append("status = ?")
            params.append(status)
        
        if files_generated is not None:
            updates.append("files_generated = ?")
            params.append(files_generated)
        
        if duration_seconds is not None:
            updates.append("duration_seconds = ?")
            params.append(duration_seconds)
        
        if messages is not None:
            updates.append("messages = ?")
            params.append(json.dumps(messages))
        
        if updates:
            params.append(run_id)
            query = f"UPDATE sessions SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
        
        conn.close()
    
    def add_file(self, run_id: str, filename: str, content: str):
        """Add a generated file to the session."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO session_files (session_id, filename, content)
            VALUES (?, ?, ?)
        """, (run_id, filename, content))
        
        # Update file count
        cursor.execute("""
            UPDATE sessions
            SET files_generated = (
                SELECT COUNT(*) FROM session_files WHERE session_id = ?
            )
            WHERE id = ?
        """, (run_id, run_id))
        
        conn.commit()
        conn.close()
    
    def get_session(self, run_id: str) -> Optional[Dict]:
        """Get a specific session by ID."""
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM sessions WHERE id = ?
        """, (run_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return dict(row)
    
    def list_sessions(self, limit: int = 50) -> List[Dict]:
        """List recent sessions."""
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, goal, timestamp, status, files_generated, duration_seconds
            FROM sessions
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        sessions = []
        for row in rows:
            session = dict(row)
            if session.get('duration_seconds'):
                mins = session['duration_seconds'] // 60
                secs = session['duration_seconds'] % 60
                session['duration'] = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
            sessions.append(session)
        
        return sessions
    
    def get_session_files(self, run_id: str) -> List[Dict]:
        """Get all files generated in a session."""
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT filename, content, created_at
            FROM session_files
            WHERE session_id = ?
            ORDER BY created_at ASC
        """, (run_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]


# Global instance
session_history = SessionHistory()
