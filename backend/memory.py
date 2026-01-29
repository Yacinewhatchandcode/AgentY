"""
Cognee Memory Adapter for AgentY
=================================
Provides persistent memory (Plans, Decisions, Code) for agents.
Falls back to local SQLite + in-memory if Cognee SDK not available.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Try to import Cognee, fall back to local implementation
try:
    import cognee
    COGNEE_AVAILABLE = True
except ImportError:
    COGNEE_AVAILABLE = False
    print("[Memory] Cognee SDK not found, using local SQLite fallback")


class MemoryStore:
    """
    Unified memory interface for AgentY.
    Stores agent artifacts (plans, code, tests, decisions) with semantic search.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path.home() / ".agenty" / "memory.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database for local storage."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                artifact_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_run_id ON artifacts(run_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_type ON artifacts(artifact_type)
        """)
        conn.commit()
        conn.close()
    
    def store(self, run_id: str, artifact_type: str, content: Any, metadata: Optional[Dict] = None) -> int:
        """
        Store an artifact in memory.
        
        Args:
            run_id: Unique identifier for the agent run
            artifact_type: Type of artifact (plan, code, test, decision, log)
            content: The actual content (will be JSON serialized if dict/list)
            metadata: Optional metadata (tags, file paths, etc.)
        
        Returns:
            The artifact ID
        """
        if isinstance(content, (dict, list)):
            content = json.dumps(content)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute(
            "INSERT INTO artifacts (run_id, artifact_type, content, metadata) VALUES (?, ?, ?, ?)",
            (run_id, artifact_type, content, json.dumps(metadata or {}))
        )
        artifact_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"[Memory] Stored {artifact_type} for run {run_id[:8]}...")
        return artifact_id
    
    def search(self, query: str, top_k: int = 5, artifact_type: Optional[str] = None) -> List[Dict]:
        """
        Search for relevant artifacts.
        
        Note: This is a simple keyword search. For semantic search,
        integrate Cognee or add FAISS/vector embeddings.
        """
        conn = sqlite3.connect(str(self.db_path))
        
        if artifact_type:
            cursor = conn.execute(
                """
                SELECT id, run_id, artifact_type, content, metadata, created_at
                FROM artifacts
                WHERE artifact_type = ? AND content LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (artifact_type, f"%{query}%", top_k)
            )
        else:
            cursor = conn.execute(
                """
                SELECT id, run_id, artifact_type, content, metadata, created_at
                FROM artifacts
                WHERE content LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (f"%{query}%", top_k)
            )
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "run_id": row[1],
                "artifact_type": row[2],
                "content": row[3][:500],  # Truncate for preview
                "metadata": json.loads(row[4]) if row[4] else {},
                "created_at": row[5]
            })
        
        conn.close()
        return results
    
    def get_run_history(self, run_id: str) -> List[Dict]:
        """Get all artifacts for a specific run."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute(
            """
            SELECT id, artifact_type, content, metadata, created_at
            FROM artifacts
            WHERE run_id = ?
            ORDER BY created_at ASC
            """,
            (run_id,)
        )
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "artifact_type": row[1],
                "content": row[2],
                "metadata": json.loads(row[3]) if row[3] else {},
                "created_at": row[4]
            })
        
        conn.close()
        return results
    
    def get_recent_runs(self, limit: int = 10) -> List[Dict]:
        """Get recent run summaries."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute(
            """
            SELECT DISTINCT run_id, MIN(created_at) as started_at
            FROM artifacts
            GROUP BY run_id
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,)
        )
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "run_id": row[0],
                "started_at": row[1]
            })
        
        conn.close()
        return results


# Singleton instance
_memory_store: Optional[MemoryStore] = None

def get_memory() -> MemoryStore:
    """Get the global memory store instance."""
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore()
    return _memory_store


if __name__ == "__main__":
    # Test the memory store
    memory = get_memory()
    
    test_run_id = "test-run-001"
    memory.store(test_run_id, "plan", {"goal": "Build a snake game", "steps": ["Create game.py", "Add controls"]})
    memory.store(test_run_id, "code", "def main():\n    print('Snake game')", {"file": "game.py"})
    
    print("\nSearch results for 'snake':")
    for result in memory.search("snake"):
        print(f"  - [{result['artifact_type']}] {result['content'][:50]}...")
    
    print("\nRun history:")
    for artifact in memory.get_run_history(test_run_id):
        print(f"  - {artifact['artifact_type']}: {artifact['content'][:30]}...")
