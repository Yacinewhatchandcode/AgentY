"""
AgentY Graph Memory System
Semantic memory with embeddings and graph relationships.
Works as a local alternative to Cognee for Python 3.14+
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
import hashlib


class GraphMemory:
    """
    Semantic graph memory for AgentY agents.
    Stores entities, relationships, and learnings with search capability.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = Path.home() / ".agenty" / "graph_memory.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize the graph memory database."""
        conn = sqlite3.connect(str(self.db_path))
        
        # Entities table - nodes in the graph
        conn.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,  -- 'agent', 'file', 'error', 'fix', 'pattern'
                name TEXT NOT NULL,
                content TEXT,
                metadata TEXT,  -- JSON
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Relationships table - edges in the graph
        conn.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relationship TEXT NOT NULL,  -- 'caused', 'fixed_by', 'depends_on', 'learned_from'
                weight REAL DEFAULT 1.0,
                metadata TEXT,  -- JSON
                created_at TEXT,
                FOREIGN KEY (source_id) REFERENCES entities(id),
                FOREIGN KEY (target_id) REFERENCES entities(id)
            )
        """)
        
        # Learnings table - stored knowledge
        conn.execute("""
            CREATE TABLE IF NOT EXISTS learnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT NOT NULL,
                category TEXT NOT NULL,  -- 'error_pattern', 'fix_pattern', 'best_practice'
                pattern TEXT NOT NULL,  -- The pattern/error signature
                solution TEXT,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                last_used TEXT,
                metadata TEXT,  -- JSON
                created_at TEXT
            )
        """)
        
        # Search index for fast text matching
        conn.execute("""
            CREATE TABLE IF NOT EXISTS search_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                keywords TEXT NOT NULL,
                created_at TEXT
            )
        """)
        
        # Create indices
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_learnings_pattern ON learnings(pattern)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_search_keywords ON search_index(keywords)")
        
        conn.commit()
        conn.close()
    
    def _generate_id(self, content: str) -> str:
        """Generate a unique ID from content."""
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def add_entity(
        self,
        entity_type: str,
        name: str,
        content: str = "",
        metadata: Optional[Dict] = None
    ) -> str:
        """Add an entity to the graph."""
        entity_id = self._generate_id(f"{entity_type}:{name}:{content[:100]}")
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(str(self.db_path))
        
        # Check if entity exists
        existing = conn.execute(
            "SELECT id FROM entities WHERE id = ?",
            (entity_id,)
        ).fetchone()
        
        if existing:
            # Update existing
            conn.execute(
                "UPDATE entities SET content = ?, metadata = ?, updated_at = ? WHERE id = ?",
                (content, json.dumps(metadata or {}), now, entity_id)
            )
        else:
            # Insert new
            conn.execute(
                """INSERT INTO entities (id, type, name, content, metadata, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (entity_id, entity_type, name, content, json.dumps(metadata or {}), now, now)
            )
            
            # Add to search index
            keywords = f"{entity_type} {name} {content}".lower()
            conn.execute(
                "INSERT INTO search_index (entity_type, entity_id, keywords, created_at) VALUES (?, ?, ?, ?)",
                (entity_type, entity_id, keywords, now)
            )
        
        conn.commit()
        conn.close()
        return entity_id
    
    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        weight: float = 1.0,
        metadata: Optional[Dict] = None
    ):
        """Add a relationship between entities."""
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            """INSERT INTO relationships (source_id, target_id, relationship, weight, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (source_id, target_id, relationship, weight, json.dumps(metadata or {}), now)
        )
        conn.commit()
        conn.close()
    
    def learn_pattern(
        self,
        agent: str,
        category: str,
        pattern: str,
        solution: str,
        metadata: Optional[Dict] = None
    ) -> int:
        """Store a learned pattern for future use."""
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(str(self.db_path))
        
        # Check if pattern already exists
        existing = conn.execute(
            "SELECT id, success_count FROM learnings WHERE agent = ? AND pattern = ?",
            (agent, pattern)
        ).fetchone()
        
        if existing:
            # Update existing pattern
            conn.execute(
                """UPDATE learnings 
                   SET solution = ?, success_count = success_count + 1, last_used = ?, metadata = ?
                   WHERE id = ?""",
                (solution, now, json.dumps(metadata or {}), existing[0])
            )
            learning_id = existing[0]
        else:
            # Insert new pattern
            cursor = conn.execute(
                """INSERT INTO learnings (agent, category, pattern, solution, success_count, last_used, metadata, created_at)
                   VALUES (?, ?, ?, ?, 1, ?, ?, ?)""",
                (agent, category, pattern, solution, now, json.dumps(metadata or {}), now)
            )
            learning_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return learning_id
    
    def find_similar_patterns(
        self,
        query: str,
        agent: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """Find patterns similar to the query."""
        conn = sqlite3.connect(str(self.db_path))
        
        # Simple keyword matching (could be enhanced with proper embeddings)
        query_words = query.lower().split()
        
        sql = "SELECT * FROM learnings WHERE 1=1"
        params = []
        
        if agent:
            sql += " AND agent = ?"
            params.append(agent)
        
        if category:
            sql += " AND category = ?"
            params.append(category)
        
        # Order by success count (proven solutions first)
        sql += " ORDER BY success_count DESC, last_used DESC LIMIT ?"
        params.append(limit * 3)  # Get more to filter
        
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        
        # Score by keyword match
        results = []
        for row in rows:
            pattern = row[3].lower()
            solution = (row[4] or "").lower()
            
            score = 0
            for word in query_words:
                if word in pattern:
                    score += 2
                if word in solution:
                    score += 1
            
            if score > 0:
                results.append({
                    "id": row[0],
                    "agent": row[1],
                    "category": row[2],
                    "pattern": row[3],
                    "solution": row[4],
                    "success_count": row[5],
                    "score": score
                })
        
        # Sort by score and return top results
        results.sort(key=lambda x: (-x["score"], -x["success_count"]))
        return results[:limit]
    
    def search(self, query: str, entity_type: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Search entities by keyword."""
        conn = sqlite3.connect(str(self.db_path))
        
        query_lower = query.lower()
        
        sql = """
            SELECT e.* FROM entities e
            JOIN search_index s ON e.id = s.entity_id
            WHERE s.keywords LIKE ?
        """
        params = [f"%{query_lower}%"]
        
        if entity_type:
            sql += " AND e.type = ?"
            params.append(entity_type)
        
        sql += " ORDER BY e.updated_at DESC LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "type": row[1],
                "name": row[2],
                "content": row[3],
                "metadata": json.loads(row[4] or "{}"),
                "created_at": row[5]
            })
        
        return results
    
    def get_related(self, entity_id: str, relationship: Optional[str] = None) -> List[Dict]:
        """Get entities related to the given entity."""
        conn = sqlite3.connect(str(self.db_path))
        
        sql = """
            SELECT e.*, r.relationship, r.weight
            FROM entities e
            JOIN relationships r ON e.id = r.target_id
            WHERE r.source_id = ?
        """
        params = [entity_id]
        
        if relationship:
            sql += " AND r.relationship = ?"
            params.append(relationship)
        
        sql += " ORDER BY r.weight DESC"
        
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "type": row[1],
                "name": row[2],
                "content": row[3],
                "metadata": json.loads(row[4] or "{}"),
                "relationship": row[7],
                "weight": row[8]
            })
        
        return results
    
    def record_error_fix(
        self,
        error_type: str,
        error_message: str,
        file_name: str,
        fix_applied: str,
        agent: str = "Debugger"
    ):
        """Record an error and its fix for future learning."""
        # Create error entity
        error_id = self.add_entity(
            entity_type="error",
            name=error_type,
            content=error_message[:500],
            metadata={"file": file_name}
        )
        
        # Create fix entity
        fix_id = self.add_entity(
            entity_type="fix",
            name=f"Fix for {error_type}",
            content=fix_applied[:1000],
            metadata={"file": file_name, "agent": agent}
        )
        
        # Create relationship
        self.add_relationship(
            source_id=error_id,
            target_id=fix_id,
            relationship="fixed_by",
            weight=1.0,
            metadata={"agent": agent}
        )
        
        # Store as learning pattern
        self.learn_pattern(
            agent=agent,
            category="error_pattern",
            pattern=f"{error_type}: {error_message[:200]}",
            solution=fix_applied[:500],
            metadata={"file": file_name}
        )
        
        return error_id, fix_id
    
    def get_stats(self) -> Dict:
        """Get memory statistics."""
        conn = sqlite3.connect(str(self.db_path))
        
        stats = {
            "entities": conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0],
            "relationships": conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0],
            "learnings": conn.execute("SELECT COUNT(*) FROM learnings").fetchone()[0],
            "entity_types": {},
            "top_learnings": []
        }
        
        # Entity type breakdown
        for row in conn.execute("SELECT type, COUNT(*) FROM entities GROUP BY type"):
            stats["entity_types"][row[0]] = row[1]
        
        # Top learnings
        for row in conn.execute(
            "SELECT agent, pattern, solution, success_count FROM learnings ORDER BY success_count DESC LIMIT 5"
        ):
            stats["top_learnings"].append({
                "agent": row[0],
                "pattern": row[1][:50],
                "solution": row[2][:50] if row[2] else None,
                "success_count": row[3]
            })
        
        conn.close()
        return stats


# Global instance
_graph_memory: Optional[GraphMemory] = None

def get_graph_memory() -> GraphMemory:
    """Get the global graph memory instance."""
    global _graph_memory
    if _graph_memory is None:
        _graph_memory = GraphMemory()
    return _graph_memory
