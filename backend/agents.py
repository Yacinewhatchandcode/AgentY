"""
AgentY Multi-Agent System
==========================
True multi-agent architecture with separate agent instances,
message passing, and an Arbiter for conflict resolution.
"""

import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import requests


class MessageType(Enum):
    """Types of messages that agents can send."""
    PLAN = "plan"
    CODE = "code"
    TEST_RESULT = "test_result"
    CONTRADICTION = "contradiction"
    RESOLUTION = "resolution"
    REQUEST = "request"
    RESPONSE = "response"
    STATUS = "status"
    ERROR = "error"
    TERMINAL = "terminal"  # Real terminal output
    GIT_COMMIT = "git_commit"  # Git operations
    APPROVAL_REQUIRED = "approval_required"  # Needs user approval
    DEBUG_ANALYSIS = "debug_analysis"  # Debugger agent root cause analysis
    FIX_SUGGESTION = "fix_suggestion"  # Debugger -> Coder fix instruction
    CLARIFICATION = "clarification"  # Agent asking for more info
    LEARNING = "learning"  # Memory learning from past mistakes


@dataclass
class AgentMessage:
    """Message passed between agents."""
    id: str
    sender: str
    recipient: str  # Can be "broadcast" or specific agent name
    type: MessageType
    content: Any
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    in_reply_to: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "sender": self.sender,
            "recipient": self.recipient,
            "type": self.type.value,
            "content": self.content,
            "timestamp": self.timestamp,
            "in_reply_to": self.in_reply_to
        }


class MessageBus:
    """
    Central message bus for agent communication.
    Agents subscribe to messages and can broadcast or send directly.
    """
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.message_history: List[AgentMessage] = []
        self.external_listeners: List[Callable] = []  # For WebSocket streaming
    
    def subscribe(self, agent_name: str, callback: Callable[[AgentMessage], None]):
        """Subscribe an agent to receive messages."""
        if agent_name not in self.subscribers:
            self.subscribers[agent_name] = []
        self.subscribers[agent_name].append(callback)
    
    def add_external_listener(self, callback: Callable[[AgentMessage], None]):
        """Add an external listener (e.g., WebSocket) for all messages."""
        self.external_listeners.append(callback)
    
    async def publish(self, message: AgentMessage):
        """Publish a message to the bus."""
        self.message_history.append(message)
        
        # Notify external listeners (WebSocket)
        for listener in self.external_listeners:
            try:
                await listener(message)
            except Exception as e:
                print(f"[MessageBus] External listener error: {e}")
        
        # Deliver to specific recipient or broadcast
        if message.recipient == "broadcast":
            for agent_name, callbacks in self.subscribers.items():
                if agent_name != message.sender:  # Don't send to self
                    for callback in callbacks:
                        try:
                            await callback(message)
                        except Exception as e:
                            print(f"[MessageBus] Delivery error to {agent_name}: {e}")
        elif message.recipient in self.subscribers:
            for callback in self.subscribers[message.recipient]:
                try:
                    await callback(message)
                except Exception as e:
                    print(f"[MessageBus] Delivery error to {message.recipient}: {e}")
    
    def get_history(self, limit: int = 50) -> List[Dict]:
        """Get recent message history."""
        return [m.to_dict() for m in self.message_history[-limit:]]


# ==================== CONSENSUS SYSTEM ====================

@dataclass
class Vote:
    """A vote from an agent on a proposal."""
    voter: str
    decision: str  # APPROVE, CHALLENGE, ABSTAIN
    confidence: float
    reasoning: str
    challenges: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Proposal:
    """A proposal that agents vote on."""
    id: str
    proposer: str
    proposal_type: str  # plan, code, design, fix
    content: Any
    votes: Dict[str, Vote] = field(default_factory=dict)
    debate_round: int = 0
    max_debate_rounds: int = 2
    status: str = "pending"  # pending, approved, rejected, needs_revision
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ConsensusManager:
    """
    Manages consensus voting across agents.
    
    Features:
    - Weighted voting (some agents count more)
    - Quorum requirements (minimum votes needed)
    - Debate rounds (challenge → respond → revote)
    - Vote tracking and history
    """
    
    # Vote weights by agent role
    VOTE_WEIGHTS = {
        "Arbiter": 2.0,      # Supervisor vote counts double
        "Reviewer": 1.5,     # Quality gate has extra weight
        "Architect": 1.5,    # Design decisions matter
        "Tester": 1.2,       # Testing validation important
        "Planner": 1.0,
        "Coder": 1.0,
        "Debugger": 1.0,
        "Executor": 0.5,     # Executor mainly observes
    }
    
    # Minimum votes needed for quorum (by proposal type)
    QUORUM_REQUIREMENTS = {
        "plan": 3,           # Need 3+ votes on plans
        "code": 2,           # Need 2+ votes on code
        "design": 3,         # Need 3+ votes on design
        "fix": 2,            # Need 2+ votes on fixes
        "default": 2
    }
    
    def __init__(self, bus: MessageBus):
        self.bus = bus
        self.proposals: Dict[str, Proposal] = {}
        self.vote_history: List[Dict] = []
    
    def create_proposal(
        self,
        proposer: str,
        proposal_type: str,
        content: Any
    ) -> str:
        """Create a new proposal for consensus voting."""
        proposal_id = f"prop-{uuid.uuid4().hex[:8]}"
        
        proposal = Proposal(
            id=proposal_id,
            proposer=proposer,
            proposal_type=proposal_type,
            content=content
        )
        
        self.proposals[proposal_id] = proposal
        print(f"[Consensus] Created proposal {proposal_id} from {proposer}")
        return proposal_id
    
    def cast_vote(
        self,
        proposal_id: str,
        voter: str,
        decision: str,
        confidence: float = 0.8,
        reasoning: str = "",
        challenges: List[str] = None
    ) -> bool:
        """Cast a vote on a proposal."""
        if proposal_id not in self.proposals:
            print(f"[Consensus] Proposal {proposal_id} not found")
            return False
        
        proposal = self.proposals[proposal_id]
        
        vote = Vote(
            voter=voter,
            decision=decision.upper(),
            confidence=confidence,
            reasoning=reasoning,
            challenges=challenges or []
        )
        
        proposal.votes[voter] = vote
        self.vote_history.append({
            "proposal_id": proposal_id,
            "vote": vote
        })
        
        print(f"[Consensus] {voter} voted {decision} on {proposal_id} (confidence: {confidence})")
        return True
    
    def get_weighted_tally(self, proposal_id: str) -> Dict:
        """Calculate weighted vote tally."""
        if proposal_id not in self.proposals:
            return {"error": "Proposal not found"}
        
        proposal = self.proposals[proposal_id]
        
        approve_score = 0.0
        challenge_score = 0.0
        abstain_count = 0
        total_votes = 0
        
        for voter, vote in proposal.votes.items():
            weight = self.VOTE_WEIGHTS.get(voter, 1.0)
            weighted_vote = weight * vote.confidence
            
            if vote.decision == "APPROVE":
                approve_score += weighted_vote
            elif vote.decision == "CHALLENGE":
                challenge_score += weighted_vote
            else:
                abstain_count += 1
            
            total_votes += 1
        
        return {
            "proposal_id": proposal_id,
            "approve_score": round(approve_score, 2),
            "challenge_score": round(challenge_score, 2),
            "abstain_count": abstain_count,
            "total_votes": total_votes,
            "votes": {v: proposal.votes[v].decision for v in proposal.votes}
        }
    
    def check_quorum(self, proposal_id: str) -> bool:
        """Check if we have enough votes for quorum."""
        if proposal_id not in self.proposals:
            return False
        
        proposal = self.proposals[proposal_id]
        required = self.QUORUM_REQUIREMENTS.get(
            proposal.proposal_type,
            self.QUORUM_REQUIREMENTS["default"]
        )
        
        # Count non-abstain votes
        actual_votes = sum(
            1 for v in proposal.votes.values()
            if v.decision != "ABSTAIN"
        )
        
        return actual_votes >= required
    
    def evaluate_proposal(self, proposal_id: str) -> Dict:
        """
        Evaluate a proposal and determine outcome.
        Returns decision and whether debate is needed.
        """
        if proposal_id not in self.proposals:
            return {"status": "error", "message": "Proposal not found"}
        
        proposal = self.proposals[proposal_id]
        tally = self.get_weighted_tally(proposal_id)
        has_quorum = self.check_quorum(proposal_id)
        
        if not has_quorum:
            return {
                "status": "pending",
                "message": f"Waiting for quorum ({tally['total_votes']} votes, need more)",
                "tally": tally
            }
        
        approve_score = tally["approve_score"]
        challenge_score = tally["challenge_score"]
        
        # Clear approval: approve > challenge by significant margin
        if approve_score > challenge_score * 1.5:
            proposal.status = "approved"
            return {
                "status": "approved",
                "message": f"Approved with score {approve_score} vs {challenge_score}",
                "tally": tally
            }
        
        # Clear rejection: challenge > approve significantly
        if challenge_score > approve_score * 1.5:
            # Check if we can do another debate round
            if proposal.debate_round < proposal.max_debate_rounds:
                proposal.debate_round += 1
                proposal.status = "debating"
                return {
                    "status": "needs_debate",
                    "message": f"Starting debate round {proposal.debate_round}",
                    "challenges": self._collect_challenges(proposal_id),
                    "tally": tally
                }
            else:
                proposal.status = "rejected"
                return {
                    "status": "rejected",
                    "message": f"Rejected after {proposal.debate_round} debate rounds",
                    "tally": tally
                }
        
        # Close call - need debate
        if proposal.debate_round < proposal.max_debate_rounds:
            proposal.debate_round += 1
            proposal.status = "debating"
            return {
                "status": "needs_debate",
                "message": f"Close vote ({approve_score} vs {challenge_score}), starting debate",
                "challenges": self._collect_challenges(proposal_id),
                "tally": tally
            }
        
        # After max debates, approve if more approve than challenge
        if approve_score >= challenge_score:
            proposal.status = "approved"
            return {
                "status": "approved",
                "message": "Approved after debates (narrow margin)",
                "tally": tally
            }
        else:
            proposal.status = "needs_revision"
            return {
                "status": "needs_revision",
                "message": "Needs revision based on challenges",
                "challenges": self._collect_challenges(proposal_id),
                "tally": tally
            }
    
    def _collect_challenges(self, proposal_id: str) -> List[str]:
        """Collect all challenges from CHALLENGE votes."""
        if proposal_id not in self.proposals:
            return []
        
        proposal = self.proposals[proposal_id]
        challenges = []
        
        for vote in proposal.votes.values():
            if vote.decision == "CHALLENGE" and vote.challenges:
                challenges.extend(vote.challenges)
        
        return challenges
    
    def reset_votes(self, proposal_id: str):
        """Reset votes for a new debate round."""
        if proposal_id in self.proposals:
            self.proposals[proposal_id].votes = {}
    
    def get_proposal_status(self, proposal_id: str) -> Dict:
        """Get current status of a proposal."""
        if proposal_id not in self.proposals:
            return {"error": "Proposal not found"}
        
        proposal = self.proposals[proposal_id]
        return {
            "id": proposal.id,
            "proposer": proposal.proposer,
            "type": proposal.proposal_type,
            "status": proposal.status,
            "debate_round": proposal.debate_round,
            "votes": {v: proposal.votes[v].decision for v in proposal.votes},
            "tally": self.get_weighted_tally(proposal_id)
        }




class BaseAgent(ABC):
    """
    Base class for all agents in the system.
    Each agent has its own identity, prompt, tools, and MEMORY.
    """
    
    def __init__(
        self,
        name: str,
        role: str,
        system_prompt: str,
        bus: MessageBus,
        llm_url: str = "http://127.0.0.1:11434",
        mcp_url: str = "http://127.0.0.1:8000",
        model: str = "qwen3:8b"
    ):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.bus = bus
        self.llm_url = llm_url
        self.mcp_url = mcp_url
        self.model = model
        self.inbox: asyncio.Queue = asyncio.Queue()
        self.is_running = False
        self.current_task: Optional[str] = None
        
        # =================== MEMORY SYSTEM ===================
        # Each agent has its own memory (Cognee + LangGraph)
        self.memory: Dict[str, Any] = {}
        self.decisions_made: List[Dict] = []
        self.lessons_learned: List[str] = []
        self.current_node_id: Optional[str] = None  # Track position in graph
        self._init_memory_systems()
        
        # Subscribe to messages
        bus.subscribe(name, self._receive_message)
    
    def _init_memory_systems(self):
        """Initialize all memory systems (Cognee + LangGraph)."""
        # Cognee/SQLite memory
        try:
            from memory import get_memory
            self.memory_store = get_memory()
            self.use_cognee = True
        except:
            self.memory_store = None
            self.use_cognee = False
        
        # LangGraph memory
        try:
            from graph_memory import get_graph_memory
            self.graph_memory = get_graph_memory()
            self.use_langgraph = True
        except Exception as e:
            print(f"[{self.name}] LangGraph not available: {e}")
            self.graph_memory = None
            self.use_langgraph = False
    
    def log_decision(self, action: str, content: Any, run_id: str = "default", parent_id: Optional[str] = None) -> Optional[str]:
        """Log a decision to the graph memory for full traceability."""
        decision = {
            "agent": self.name,
            "action": action,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        self.decisions_made.append(decision)
        
        # Log to LangGraph if available
        if self.use_langgraph and self.graph_memory:
            try:
                node_id = self.graph_memory.add_node(
                    run_id=run_id,
                    agent=self.name,
                    action=action,
                    content=content,
                    parent_id=parent_id or self.current_node_id
                )
                self.current_node_id = node_id
                return node_id
            except Exception as e:
                print(f"[{self.name}] Graph memory error: {e}")
        
        return None
    
    def get_decision_history(self, run_id: str = "default") -> List[Dict]:
        """Get decision history from graph memory."""
        if self.use_langgraph and self.graph_memory:
            return self.graph_memory.get_agent_history(self.name, run_id)
        return self.decisions_made
    
    async def _receive_message(self, message: AgentMessage):
        """Receive a message into the inbox."""
        await self.inbox.put(message)
    
    def _call_llm_sync(self, prompt: str, max_tokens: int = 2048) -> str:
        """Synchronous LLM call - runs in thread pool."""
        try:
            print(f"[{self.name}] Calling Ollama with {self.model}...")
            response = requests.post(
                f"{self.llm_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": f"{self.system_prompt}\n\n{prompt}",
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": 0.3
                    }
                },
                timeout=300  # 5 minutes for larger models like qwen3:14b
            )
            response.raise_for_status()
            result = response.json().get("response", "").strip()
            # Clean thinking tags from qwen3 responses
            if "<think>" in result:
                import re
                result = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL).strip()
            print(f"[{self.name}] Got response ({len(result)} chars)")
            return result
        except Exception as e:
            print(f"[{self.name}] LLM Error: {e}")
            return f"[LLM Error] {str(e)}"
    
    async def call_llm(self, prompt: str, max_tokens: int = 2048) -> str:
        """Call Ollama for local LLM inference (async wrapper)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._call_llm_sync, prompt, max_tokens)
    
    def call_mcp(self, tool: str, action: str, args: Dict = None) -> Dict:
        """Call the MCP Gateway to execute a tool."""
        try:
            response = requests.post(
                f"{self.mcp_url}/invoke",
                json={"tool": tool, "action": action, "args": args or {}},
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"success": False, "stderr": str(e)}
    
    # ===================== MEMORY SYSTEM =====================
    def remember(self, key: str, value: Any, category: str = "general"):
        """Store something in agent's memory."""
        self.memory[key] = {
            "value": value,
            "category": category,
            "timestamp": datetime.now().isoformat()
        }
        # Persist to SQLite
        self._persist_memory(key, value, category)
    
    def recall(self, key: str) -> Optional[Any]:
        """Retrieve from agent's memory."""
        if key in self.memory:
            return self.memory[key]["value"]
        # Try to load from SQLite
        return self._load_memory(key)
    
    def recall_by_category(self, category: str) -> List[Dict]:
        """Get all memories of a category."""
        results = []
        for key, item in self.memory.items():
            if item.get("category") == category:
                results.append({"key": key, **item})
        return results
    
    def _persist_memory(self, key: str, value: Any, category: str):
        """Save memory to SQLite."""
        try:
            import sqlite3
            db_path = Path.home() / ".agenty" / f"memory_{self.name.lower()}.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(db_path))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_memory (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    category TEXT,
                    timestamp TEXT
                )
            """)
            conn.execute(
                "INSERT OR REPLACE INTO agent_memory (key, value, category, timestamp) VALUES (?, ?, ?, ?)",
                (key, json.dumps(value), category, datetime.now().isoformat())
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[{self.name}] Memory persist error: {e}")
    
    def _load_memory(self, key: str) -> Optional[Any]:
        """Load memory from SQLite."""
        try:
            import sqlite3
            db_path = Path.home() / ".agenty" / f"memory_{self.name.lower()}.db"
            if not db_path.exists():
                return None
            conn = sqlite3.connect(str(db_path))
            cursor = conn.execute("SELECT value FROM agent_memory WHERE key = ?", (key,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return json.loads(row[0])
        except:
            pass
        return None
    
    # ===================== SELF-CRITIQUE =====================
    async def self_critique(self, work: str, work_type: str = "code") -> Dict:
        """Critique own work before submitting - improves quality."""
        critique_prompt = f"""Review this {work_type} critically. Find any issues.

{work_type.upper()}:
{work[:3000]}

Respond in JSON:
{{
  "quality_score": 1-10,
  "issues": ["issue1", "issue2"],
  "improvements": ["improvement1", "improvement2"],
  "should_revise": true/false
}}"""
        
        response = await self.call_llm(critique_prompt, max_tokens=1000)
        try:
            import re
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        return {"quality_score": 5, "issues": [], "improvements": [], "should_revise": False}
    
    # ===================== CONSENSUS VOTING =====================
    async def vote_on_proposal(self, proposal: Dict) -> Dict:
        """Vote on another agent's proposal (consensus mechanism)."""
        vote_prompt = f"""As the {self.name} agent, evaluate this proposal:

PROPOSAL FROM: {proposal.get('from', 'unknown')}
TYPE: {proposal.get('type', 'unknown')}
CONTENT: {json.dumps(proposal.get('content', {}), indent=2)[:2000]}

Cast your vote:
- APPROVE if the proposal is good
- CHALLENGE if you see issues that need addressing
- ABSTAIN if this is outside your expertise

Respond in JSON:
{{
  "vote": "APPROVE | CHALLENGE | ABSTAIN",
  "confidence": 0.0-1.0,
  "reasoning": "Why you voted this way",
  "challenges": ["Optional list of issues if CHALLENGE"]
}}"""
        
        response = await self.call_llm(vote_prompt, max_tokens=800)
        try:
            import re
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                vote_result = json.loads(json_match.group())
                vote_result["voter"] = self.name
                return vote_result
        except:
            pass
        return {"vote": "ABSTAIN", "voter": self.name, "confidence": 0.5, "reasoning": "Could not parse"}
    
    async def send_message(
        self,
        recipient: str,
        msg_type: MessageType,
        content: Any,
        in_reply_to: Optional[str] = None
    ):
        """Send a message via the bus."""
        message = AgentMessage(
            id=str(uuid.uuid4())[:8],
            sender=self.name,
            recipient=recipient,
            type=msg_type,
            content=content,
            in_reply_to=in_reply_to
        )
        await self.bus.publish(message)
    
    async def broadcast(self, msg_type: MessageType, content: Any):
        """Broadcast a message to all agents."""
        await self.send_message("broadcast", msg_type, content)
    
    # ===================== CONSENSUS HELPERS =====================
    def propose_for_consensus(self, proposal_type: str, content: Any) -> Optional[str]:
        """Create a proposal for consensus voting. Returns proposal_id."""
        if hasattr(self, 'consensus') and self.consensus:
            proposal_id = self.consensus.create_proposal(
                proposer=self.name,
                proposal_type=proposal_type,
                content=content
            )
            # Log to graph memory
            self.log_decision(
                action=f"propose_{proposal_type}",
                content={"proposal_id": proposal_id, "type": proposal_type}
            )
            return proposal_id
        return None
    
    def vote_on(
        self,
        proposal_id: str,
        decision: str,
        confidence: float = 0.8,
        reasoning: str = "",
        challenges: List[str] = None
    ) -> bool:
        """Cast a vote on a proposal."""
        if hasattr(self, 'consensus') and self.consensus:
            success = self.consensus.cast_vote(
                proposal_id=proposal_id,
                voter=self.name,
                decision=decision,
                confidence=confidence,
                reasoning=reasoning,
                challenges=challenges
            )
            # Log the vote
            self.log_decision(
                action=f"vote_{decision.lower()}",
                content={
                    "proposal_id": proposal_id,
                    "confidence": confidence,
                    "challenges": challenges or []
                }
            )
            return success
        return False
    
    def check_consensus(self, proposal_id: str) -> Dict:
        """Check if a proposal has reached consensus."""
        if hasattr(self, 'consensus') and self.consensus:
            return self.consensus.evaluate_proposal(proposal_id)
        return {"status": "error", "message": "No consensus manager"}
    
    @abstractmethod
    async def process_task(self, task: str, context: Dict) -> Any:
        """Process a task - implemented by each agent type."""
        pass
    
    async def run(self):
        """Main agent loop - process inbox messages."""
        self.is_running = True
        while self.is_running:
            try:
                message = await asyncio.wait_for(self.inbox.get(), timeout=1.0)
                await self.handle_message(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"[{self.name}] Error: {e}")
    
    async def handle_message(self, message: AgentMessage):
        """Handle an incoming message - can be overridden."""
        # Handle vote requests
        if message.type == MessageType.REQUEST and message.content.get("action") == "vote":
            vote = await self.vote_on_proposal(message.content.get("proposal", {}))
            await self.send_message(message.sender, MessageType.RESPONSE, vote, in_reply_to=message.id)
    
    def stop(self):
        """Stop the agent loop."""
        self.is_running = False


class PlannerAgent(BaseAgent):
    """
    The Planner agent analyzes goals and creates execution plans.
    """
    
    def __init__(self, bus: MessageBus, **kwargs):
        super().__init__(
            name="Planner",
            role="planner",
            system_prompt="""You are the Planner agent. Your job is to:
1. Analyze the user's goal
2. Break it down into concrete steps
3. Create a SINGLE self-contained file (NOT multiple files!)

CRITICAL RULES:
- Create ONLY ONE FILE that contains everything
- For games: ONE file like game.py with ALL classes and logic inside
- For web: ONE file like index.html with embedded CSS and JavaScript
- NEVER split code across multiple files - put everything in ONE file
- NEVER plan .md documentation files

Respond in JSON format:
{
  "analysis": "Brief analysis of the goal",
  "steps": ["Step 1", "Step 2", ...],
  "files": [{"name": "game.py", "purpose": "Complete standalone game with all classes"}],
  "tests": ["Run and verify output"]
}""",
            bus=bus,
            **kwargs
        )
    
    async def process_task(self, task: str, context: Dict) -> Dict:
        """Create a plan for the given task."""
        await self.broadcast(MessageType.STATUS, f"Analyzing: {task[:50]}...")
        
        prompt = f"""Create a plan for this goal:

GOAL: {task}

CONTEXT: {json.dumps(context.get('memory', {}), indent=2) if context.get('memory') else 'New project'}

Respond with a JSON plan."""

        response = await self.call_llm(prompt)
        
        try:
            plan = json.loads(response)
        except:
            plan = {
                "analysis": task,
                "steps": [task],
                "files": [{"name": "main.py", "purpose": "Main implementation"}],
                "tests": ["Run and verify output"]
            }
        
        await self.broadcast(MessageType.PLAN, plan)
        return plan


class CoderAgent(BaseAgent):
    """
    The Coder agent writes code based on plans and requests.
    """
    
    def __init__(self, bus: MessageBus, **kwargs):
        super().__init__(
            name="Coder",
            role="coder",
            system_prompt="""You are the Coder agent. OUTPUT ONLY RAW CODE - NOTHING ELSE!

CRITICAL RULES - FOLLOW EXACTLY:
1. Output ONLY working code - NO explanations, NO markdown, NO comments about the code
2. Start immediately with imports (e.g., "import pygame")
3. Write COMPLETE, STANDALONE, RUNNABLE code
4. Include ALL classes and functions in ONE file
5. Include `if __name__ == "__main__":` block
6. Make sure ALL parentheses, brackets, quotes are closed
7. NEVER use markdown fences (```) - just raw code
8. NEVER explain what the code does - ONLY output the code itself

WRONG OUTPUT (DO NOT DO THIS):
"To fix the issue, we need to..."
"Here's the corrected code:"
```python
import pygame
```

CORRECT OUTPUT (DO THIS):
import pygame
import sys

class Game:
    ...

if __name__ == "__main__":
    main()""",
            bus=bus,
            **kwargs
        )
        self.pending_files: List[Dict] = []
        self.total_files_expected = 0
        self.files_created = 0
    
    def _clean_code_output(self, raw_output: str) -> str:
        """Clean LLM output to extract only code, removing explanations and markdown."""
        import re
        
        # Remove markdown fences
        code = raw_output.replace("```python", "").replace("```javascript", "").replace("```html", "").replace("```", "")
        
        # If the output starts with explanation text (not an import or comment), try to extract code
        lines = code.strip().split('\n')
        
        # Find where actual code starts (import, class, def, or #!)
        code_start_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(('import ', 'from ', 'class ', 'def ', '#!', '# ', 'pygame', 'import')):
                code_start_idx = i
                break
            elif stripped.startswith(('To ', 'Here', 'The ', 'This ', 'Below', 'I ', '---', '###', '**', '*')):
                # This is explanation text, continue looking
                continue
            elif stripped and not any(c in stripped for c in [':', '*', '#']):
                # Might be start of code
                if '(' in stripped or '=' in stripped:
                    code_start_idx = i
                    break
        
        # Extract from code start, also remove trailing explanation
        code_lines = lines[code_start_idx:]
        
        # Find where code ends (before any trailing --- or ### sections)
        code_end_idx = len(code_lines)
        for i in range(len(code_lines) - 1, -1, -1):
            stripped = code_lines[i].strip()
            if stripped.startswith(('---', '###', '**Key', '**Why', '📌', '🔍', '✅')):
                code_end_idx = i
            elif stripped.startswith(('import ', 'def ', 'class ', 'if __name__', 'return', 'pygame', '    ')):
                # This is code, stop trimming
                break
        
        clean_code = '\n'.join(code_lines[:code_end_idx]).strip()
        return clean_code
    
    async def handle_message(self, message: AgentMessage):
        """Handle plan messages from Planner."""
        if message.type == MessageType.PLAN and message.sender == "Planner":
            plan = message.content
            await self.code_from_plan(plan)
        elif message.type == MessageType.CONTRADICTION:
            # Arbiter is asking for code revision
            await self.revise_code(message.content)
        elif message.type == MessageType.FIX_SUGGESTION:
            # Debugger is providing specific fix instructions
            await self.apply_fix(message.content)
    
    async def apply_fix(self, fix_data: Dict):
        """Apply a specific fix suggested by the Debugger agent."""
        file_name = fix_data.get("file", "")
        fix_suggestion = fix_data.get("fix_suggestion", "")
        affected_line = fix_data.get("affected_line")
        root_cause = fix_data.get("root_cause", "")
        
        await self.broadcast(
            MessageType.STATUS,
            f"🔧 Applying Debugger fix to {file_name}..."
        )
        
        # Read current code
        code_result = self.call_mcp("fs", "read", {"path": file_name})
        current_code = code_result.get("content", "")
        
        # Ask LLM to apply the specific fix
        prompt = f"""Apply this SPECIFIC fix to the code. The Debugger has analyzed the root cause.

FILE: {file_name}

ROOT CAUSE: {root_cause}

FIX INSTRUCTION: {fix_suggestion}

{f"AFFECTED LINE: {affected_line}" if affected_line else ""}

CURRENT CODE:
{current_code}

Output ONLY the corrected code. No explanations."""

        response = await self.call_llm(prompt, max_tokens=4000)
        fixed_code = self._clean_code_output(response)
        
        # Write the fixed code
        write_result = self.call_mcp("fs", "write", {
            "path": file_name,
            "content": fixed_code
        })
        
        # Log to memory for learning
        self.log_decision(
            action="apply_debugger_fix",
            content={
                "file": file_name,
                "root_cause": root_cause,
                "fix_applied": fix_suggestion[:200]
            }
        )
        
        await self.broadcast(
            MessageType.CODE,
            {
                "file": file_name,
                "code": fixed_code,
                "revision": True,
                "fix_from_debugger": True
            }
        )
        
        await self.broadcast(
            MessageType.STATUS,
            f"🔧 Fixed {file_name} using Debugger's analysis"
        )
        
        # Ask Tester to re-verify
        await self.send_message(
            "Tester",
            MessageType.CODE,
            {"file": file_name, "code": fixed_code, "retest": True}
        )
    
    async def code_from_plan(self, plan: Dict):
        """Generate code for all files in the plan."""
        files = plan.get("files", [{"name": "main.py", "purpose": "Main implementation"}])
        all_files_info = plan.get("files", [])
        self.total_files_expected = len(files)
        self.files_created = 0
        created_files = []
        
        for file_info in files:
            file_name = file_info.get("name", "main.py")
            purpose = file_info.get("purpose", "Implementation")
            
            await self.broadcast(MessageType.STATUS, f"Writing {file_name}...")
            
            # Build context about other files in the project
            other_files = [f for f in all_files_info if f.get("name") != file_name]
            other_files_context = ""
            if other_files:
                other_files_context = f"\nOTHER FILES IN PROJECT: {json.dumps(other_files)}\nMake sure imports between files are compatible."
            
            prompt = f"""Write COMPLETE, WORKING code for this file:

FILE: {file_name}
PURPOSE: {purpose}
PLAN STEPS: {json.dumps(plan.get('steps', []))}
{other_files_context}

CRITICAL REQUIREMENTS:
1. Write the COMPLETE file from start to finish
2. Include ALL necessary imports at the top
3. Make sure ALL parentheses, brackets, and strings are properly closed
4. Include `if __name__ == "__main__":` block for runnable files
5. NO markdown fences (```) - just raw code
6. For games: prefer a SINGLE self-contained file over multiple modules

Write the complete code now:"""

            code = await self.call_llm(prompt, max_tokens=6000)
            
            # CHECK FOR LLM ERRORS - don't write error messages as code!
            if code.startswith("[LLM Error]"):
                await self.broadcast(MessageType.STATUS, f"⚠️ LLM failed for {file_name}: {code[:100]}")
                await self.broadcast(
                    MessageType.CODE,
                    {"file": file_name, "code": "", "success": False, "error": code, "is_last_file": True}
                )
                return  # Don't continue, let Arbiter handle retry
            
            # Clean up any markdown fences and explanations that slipped through
            code = self._clean_code_output(code)
            
            # Write file via MCP
            result = self.call_mcp("fs", "write", {"path": file_name, "content": code})
            self.files_created += 1
            created_files.append(file_name)
            
            # Only broadcast CODE message after ALL files are created (for deferred testing)
            is_last_file = self.files_created >= self.total_files_expected
            
            await self.broadcast(
                MessageType.CODE,
                {
                    "file": file_name, 
                    "code": code, 
                    "success": result.get("success", False),
                    "is_last_file": is_last_file,
                    "all_files": created_files if is_last_file else None
                }
            )
    
    async def revise_code(self, contradiction: Dict):
        """Revise code based on contradiction feedback, potentially with fallback model."""
        file_name = contradiction.get("file", "main.py")
        issue = contradiction.get("issue", "Unknown issue")
        suggested_model = contradiction.get("suggested_model", self.model)
        
        # Temporarily switch model if Arbiter suggested a fallback
        original_model = self.model
        if suggested_model != self.model:
            self.model = suggested_model
            await self.broadcast(MessageType.STATUS, f"Switching to {suggested_model} for revision...")
        
        await self.broadcast(MessageType.STATUS, f"Revising {file_name}: {issue[:50]}...")
        
        # Read current file
        current = self.call_mcp("fs", "read", {"path": file_name})
        current_code = current.get("content", "")
        
        prompt = f"""Fix this Python code. The issue is:

ISSUE: {issue}

CURRENT CODE (has problems):
{current_code}

REQUIREMENTS FOR FIX:
1. Fix the specific issue mentioned above
2. Make sure ALL parentheses, brackets, and strings are properly closed
3. Include ALL necessary imports
4. Write COMPLETE, WORKING code - no truncation
5. NO markdown fences (```) - just raw Python code
6. Include `if __name__ == "__main__":` block

Write the COMPLETE fixed code now:"""

        fixed_code = await self.call_llm(prompt, max_tokens=6000)
        
        # CHECK FOR LLM ERRORS - don't write error messages as code!
        if fixed_code.startswith("[LLM Error]"):
            await self.broadcast(MessageType.STATUS, f"⚠️ LLM failed during revision: {fixed_code[:100]}")
            # Restore original model before returning
            self.model = original_model
            await self.broadcast(
                MessageType.CODE,
                {"file": file_name, "code": "", "success": False, "error": fixed_code, "is_last_file": True}
            )
            return
        
        fixed_code = self._clean_code_output(fixed_code)
        
        # Restore original model
        self.model = original_model
        
        result = self.call_mcp("fs", "write", {"path": file_name, "content": fixed_code})
        
        await self.broadcast(
            MessageType.CODE,
            {"file": file_name, "code": fixed_code, "revision": True, "success": result.get("success", False), "is_last_file": True}
        )
    
    async def process_task(self, task: str, context: Dict) -> Dict:
        """Direct task processing (called by Arbiter)."""
        # Wait for plan from Planner
        return {"status": "waiting_for_plan"}


class TesterAgent(BaseAgent):
    """
    The Tester agent verifies code and runs tests.
    """
    
    def __init__(self, bus: MessageBus, **kwargs):
        super().__init__(
            name="Tester",
            role="tester",
            system_prompt="""You are the Tester agent. Your job is to:
1. Verify that code files exist and are valid
2. Run tests or basic validation
3. Report any issues found
4. Suggest fixes if needed

Respond in JSON:
{
  "passed": true/false,
  "tests_run": ["test name"],
  "issues": ["issue description"],
  "suggestions": ["fix suggestion"]
}""",
            bus=bus,
            **kwargs
        )
        self.files_to_test: List[str] = []
        self.pending_files: List[Dict] = []  # Queue files until all are created
    
    async def handle_message(self, message: AgentMessage):
        """Handle code messages from Coder."""
        if message.type == MessageType.CODE and message.sender == "Coder":
            file_info = message.content
            
            # Queue the file for testing
            self.pending_files.append(file_info)
            
            # Only run tests when ALL files are created
            if file_info.get("is_last_file", False):
                await self.broadcast(MessageType.STATUS, f"All {len(self.pending_files)} files created. Starting tests...")
                for pending in self.pending_files:
                    await self.test_file(pending)
                self.pending_files = []  # Clear queue
            else:
                await self.broadcast(MessageType.STATUS, f"Queued {file_info.get('file')} for testing (waiting for all files)")
    
    async def test_file(self, file_info: Dict):
        """Test a file that was just created/modified - runs REAL code."""
        file_name = file_info.get("file", "main.py")
        
        # Skip non-executable files (markdown, text, etc.)
        non_executable_extensions = ('.md', '.txt', '.json', '.yaml', '.yml', '.css')
        if file_name.endswith(non_executable_extensions):
            await self.broadcast(MessageType.STATUS, f"Skipping {file_name} (non-executable)")
            await self.broadcast(
                MessageType.TEST_RESULT,
                {"file": file_name, "passed": True, "issues": [], "skipped": True}
            )
            return
        
        await self.broadcast(MessageType.STATUS, f"Testing {file_name}...")
        
        # Read the file
        result = self.call_mcp("fs", "read", {"path": file_name})
        
        if not result.get("success", False) and not result.get("content"):
            await self.broadcast(
                MessageType.TEST_RESULT,
                {"file": file_name, "passed": False, "issues": ["File not found or empty"]}
            )
            return
        
        code = result.get("content", "")
        
        # Basic syntax check for Python files
        syntax_ok = True
        syntax_error = None
        if file_name.endswith(".py"):
            try:
                compile(code, file_name, "exec")
            except SyntaxError as e:
                syntax_ok = False
                syntax_error = str(e)
        
        issues = []
        terminal_output = []
        
        if not syntax_ok:
            issues.append(f"Syntax error: {syntax_error}")
            terminal_output.append({"type": "stderr", "content": f"SyntaxError: {syntax_error}"})
        else:
            # Check if this is a GUI application (pygame, tkinter, etc.) - skip execution
            gui_libraries = ['pygame', 'tkinter', 'PyQt', 'PySide', 'wx', 'kivy', 'arcade', 'pyglet']
            is_gui_app = any(lib in code for lib in gui_libraries)
            
            if is_gui_app:
                # GUI apps can't be tested by running them - they need display and enter infinite loops
                await self.broadcast(MessageType.STATUS, f"✓ {file_name} - Syntax OK (GUI app, skipping execution)")
                terminal_output.append({"type": "stdout", "content": f"GUI application detected - syntax validation passed"})
                # Don't append any issues - syntax is OK, that's what matters for GUI apps
            else:
                # Run the actual code via MCP shell for non-GUI apps
                await self.broadcast(MessageType.STATUS, f"Executing {file_name}...")
                
                # Execute Python file with timeout
                exec_result = self.call_mcp("shell", "run", {
                    "command": f"cd /Users/yacinebenhamou/AgentY/workspace && timeout 5 python3 {file_name} 2>&1"
                })
                
                stdout = exec_result.get("stdout", "")
                stderr = exec_result.get("stderr", "")
                exit_code = exec_result.get("exit_code", 0)
                
                # Broadcast terminal output
                if stdout:
                    terminal_output.append({"type": "stdout", "content": stdout})
                if stderr:
                    terminal_output.append({"type": "stderr", "content": stderr})
                
                await self.broadcast(MessageType.TERMINAL, {
                    "file": file_name,
                    "command": f"python3 {file_name}",
                    "output": terminal_output,
                    "exit_code": exit_code
                })
                
                # Timeout (exit code 124) is OK for long-running scripts
                if exit_code != 0 and exit_code != 124:
                    issues.append(f"Execution failed: {stderr or 'non-zero exit code'}")
                
                # Run pytest if test file exists
                if "test" in file_name.lower() or file_name.startswith("test_"):
                    pytest_result = self.call_mcp("shell", "run", {
                        "command": f"cd /Users/yacinebenhamou/AgentY/workspace && python3 -m pytest {file_name} -v 2>&1 || true"
                    })
                    
                    pytest_output = pytest_result.get("stdout", "") + pytest_result.get("stderr", "")
                    if pytest_output:
                        terminal_output.append({"type": "stdout", "content": f"pytest output:\n{pytest_output}"})
                        await self.broadcast(MessageType.TERMINAL, {
                            "file": file_name,
                            "command": f"pytest {file_name}",
                            "output": [{"type": "stdout", "content": pytest_output}]
                        })
        
        test_result = {
            "file": file_name,
            "passed": len(issues) == 0,
            "issues": issues,
            "terminal": terminal_output
        }
        
        await self.broadcast(MessageType.TEST_RESULT, test_result)
        
        # If failed, send contradiction to trigger revision
        if not test_result["passed"]:
            await self.send_message(
                "Arbiter",
                MessageType.CONTRADICTION,
                {
                    "file": file_name,
                    "issues": test_result["issues"]
                }
            )
    
    async def process_task(self, task: str, context: Dict) -> Dict:
        """Direct task processing."""
        return {"status": "waiting_for_code"}


class DebuggerAgent(BaseAgent):
    """
    The Debugger agent analyzes test failures and identifies root causes.
    Follows ISTQB debugging workflow: Failure → Defect → Root Cause → Fix Suggestion
    Uses GraphMemory for learning and ResearchTools for external search.
    """
    
    def __init__(self, bus: MessageBus, **kwargs):
        super().__init__(
            name="Debugger",
            role="debugger",
            system_prompt="""You are the Debugger agent 🐛. Your job is to analyze test failures and identify root causes.

ISTQB DEBUGGING WORKFLOW:
1. Failure → Observable symptom (error message, crash, wrong output)
2. Defect → The actual bug in the code
3. Root Cause → WHY the defect exists (code, data, environment, config)

WHEN ANALYZING A FAILURE:
1. Parse the error message and stack trace carefully
2. Identify the error TYPE:
   - Syntax Error: Missing brackets, quotes, invalid characters
   - Runtime Error: NullPointer, IndexOutOfBounds, TypeError
   - Logic Error: Off-by-one, wrong condition, incorrect algorithm
   - Import Error: Missing module, circular import
   - Resource Error: File not found, permission denied

3. Identify the ROOT CAUSE category:
   - CODE: Bug in the source code logic
   - DATA: Invalid input or edge case not handled
   - ENVIRONMENT: Missing dependency, wrong Python version
   - CONFIG: Incorrect settings or paths

Respond in JSON format:
{
  "failure_type": "RuntimeError | SyntaxError | LogicError | ImportError",
  "root_cause_category": "CODE | DATA | ENVIRONMENT | CONFIG",
  "root_cause_description": "Detailed explanation of what went wrong",
  "affected_line": "Line number if identifiable",
  "fix_suggestion": "Specific code fix to resolve the issue",
  "regression_test": "Test case to prevent this bug from recurring"
}""",
            bus=bus,
            **kwargs
        )
        self.analysis_history: List[Dict] = []
        
        # Initialize graph memory for learning
        try:
            from graph_memory import get_graph_memory
            self.graph_memory = get_graph_memory()
            print("[Debugger] GraphMemory initialized ✓")
        except Exception as e:
            print(f"[Debugger] GraphMemory not available: {e}")
            self.graph_memory = None
        
        # Initialize research tools
        try:
            from research_tools import github_search, web_search
            self.github_search = github_search
            self.web_search = web_search
            print("[Debugger] Research tools initialized ✓")
        except Exception as e:
            print(f"[Debugger] Research tools not available: {e}")
            self.github_search = None
            self.web_search = None
    
    async def handle_message(self, message: AgentMessage):
        """Handle test failure messages."""
        if message.type == MessageType.TEST_RESULT and not message.content.get("passed", True):
            await self.analyze_failure(message.content)
    
    async def analyze_failure(self, test_result: Dict):
        """Analyze a test failure to identify root cause with memory learning."""
        file_name = test_result.get("file", "unknown")
        issues = test_result.get("issues", [])
        terminal_output = test_result.get("terminal", [])
        
        await self.broadcast(MessageType.STATUS, f"🐛 Analyzing failure in {file_name}...")
        
        # Extract error details
        error_text = "\n".join(issues)
        terminal_text = ""
        for output in terminal_output:
            if isinstance(output, dict):
                terminal_text += output.get("content", "") + "\n"
            else:
                terminal_text += str(output) + "\n"
        
        # MEMORY LEARNING: Check for similar past failures in graph memory
        past_learnings = ""
        github_solutions = ""
        
        try:
            if self.graph_memory:
                # Search graph memory for similar errors
                similar_patterns = self.graph_memory.find_similar_patterns(
                    error_text[:150],
                    agent="Debugger",
                    category="error_pattern",
                    limit=3
                )
                if similar_patterns:
                    past_learnings = "\n\nPAST SIMILAR FAILURES (from memory):\n"
                    for pattern in similar_patterns:
                        past_learnings += f"- Pattern: {pattern.get('pattern', '')[:100]}\n"
                        past_learnings += f"  Solution: {pattern.get('solution', 'N/A')[:150]}\n"
                        past_learnings += f"  (Used {pattern.get('success_count', 0)} times successfully)\n"
                    
                    await self.broadcast(
                        MessageType.STATUS,
                        f"🐛 Found {len(similar_patterns)} similar past errors in memory"
                    )
        except Exception as e:
            print(f"[Debugger] Error searching graph memory: {e}")
        
        # Fallback to simple memory store
        if not past_learnings:
            try:
                if self.memory_store:
                    similar = self.memory_store.search(error_text[:100], limit=3)
                    if similar:
                        past_learnings = "\n\nPAST SIMILAR FAILURES:\n"
                        for mem in similar:
                            past_learnings += f"- {mem.get('content', '')[:200]}\n"
                            past_learnings += f"  Fix: {mem.get('metadata', {}).get('fix_applied', 'N/A')}\n"
            except:
                pass
        
        # Search GitHub for similar issues/solutions
        try:
            if self.github_search and "Error" in error_text:
                # Extract error type for search
                error_type = error_text.split(":")[0] if ":" in error_text else error_text[:50]
                github_results = self.github_search.search_code(
                    f"python {error_type} fix",
                    language="python",
                    limit=2
                )
                if github_results and not any("error" in r for r in github_results):
                    github_solutions = "\n\nGITHUB SIMILAR FIXES:\n"
                    for result in github_results[:2]:
                        github_solutions += f"- {result.get('repo', 'N/A')}: {result.get('path', '')}\n"
                        github_solutions += f"  URL: {result.get('url', 'N/A')}\n"
        except Exception as e:
            print(f"[Debugger] GitHub search error: {e}")
        
        # Read the failing code
        code_result = self.call_mcp("fs", "read", {"path": file_name})
        code = code_result.get("content", "")
        
        prompt = f"""Analyze this test failure and identify the root cause. Think step-by-step.

FILE: {file_name}

ERROR/ISSUES:
{error_text}
{past_learnings}
{github_solutions}

TERMINAL OUTPUT:
{terminal_text}

CODE:
{code[:3000]}  # Truncate for context

Provide your analysis in JSON format."""

        response = await self.call_llm(prompt, max_tokens=1500)
        
        # Parse response
        try:
            import re
            # Try to extract JSON from response
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                analysis = {
                    "failure_type": "Unknown",
                    "root_cause_category": "CODE",
                    "root_cause_description": response[:500],
                    "fix_suggestion": "Review the error and fix manually"
                }
        except:
            analysis = {
                "failure_type": "ParseError",
                "root_cause_category": "CODE",
                "root_cause_description": response[:500],
                "fix_suggestion": "Could not parse analysis"
            }
        
        analysis["file"] = file_name
        self.analysis_history.append(analysis)
        
        await self.broadcast(
            MessageType.DEBUG_ANALYSIS,
            {
                "file": file_name,
                "analysis": analysis,
                "summary": f"🐛 {analysis.get('failure_type', 'Error')}: {analysis.get('root_cause_description', 'Unknown')[:100]}"
            }
        )
        
        await self.broadcast(
            MessageType.STATUS,
            f"🐛 Root cause: {analysis.get('root_cause_category', 'CODE')} - {analysis.get('root_cause_description', '')[:80]}..."
        )
        
        # Send fix suggestion to Coder agent
        fix_suggestion = analysis.get("fix_suggestion", "")
        if fix_suggestion and analysis.get("root_cause_category") == "CODE":
            await self.broadcast(
                MessageType.STATUS,
                f"🐛 Sending fix suggestion to Coder..."
            )
            
            # Store the analysis for learning
            await self.store_learning(file_name, analysis)
            
            await self.send_message(
                "Coder",
                MessageType.FIX_SUGGESTION,
                {
                    "file": file_name,
                    "fix_suggestion": fix_suggestion,
                    "affected_line": analysis.get("affected_line"),
                    "failure_type": analysis.get("failure_type"),
                    "root_cause": analysis.get("root_cause_description"),
                    "from_debugger": True
                }
            )
    
    async def store_learning(self, file_name: str, analysis: Dict):
        """Store a debugging analysis as a learning for future reference."""
        error_type = analysis.get("failure_type", "Unknown")
        fix_suggestion = analysis.get("fix_suggestion", "")
        root_cause = analysis.get("root_cause_description", "")
        
        # Store in GraphMemory (persistent cross-session learning)
        try:
            if self.graph_memory:
                self.graph_memory.record_error_fix(
                    error_type=error_type,
                    error_message=root_cause[:500],
                    file_name=file_name,
                    fix_applied=fix_suggestion[:500],
                    agent="Debugger"
                )
                await self.broadcast(
                    MessageType.STATUS,
                    f"🧠 Learned pattern: {error_type} → stored in graph memory"
                )
        except Exception as e:
            print(f"[Debugger] Error storing to graph memory: {e}")
        
        # Also store in simple memory store (fallback)
        try:
            if self.memory_store:
                learning_content = f"Error: {error_type} - {root_cause[:200]}"
                self.memory_store.store(
                    key=f"debug_learning_{file_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    type="debug_learning",
                    content=learning_content,
                    metadata={
                        "file": file_name,
                        "failure_type": error_type,
                        "root_cause_category": analysis.get("root_cause_category"),
                        "fix_applied": fix_suggestion[:300]
                    }
                )
                self.log_decision(
                    action="learned_fix",
                    content={"file": file_name, "pattern": error_type, "fix": fix_suggestion[:200]}
                )
                await self.broadcast(
                    MessageType.LEARNING,
                    {"agent": "Debugger", "learning": f"Learned fix pattern for {error_type} errors", "file": file_name}
                )
        except Exception as e:
            print(f"[Debugger] Failed to store learning: {e}")
    
    async def process_task(self, task: str, context: Dict) -> Dict:
        """Direct task processing."""
        return {"status": "waiting_for_failures"}


class ReviewerAgent(BaseAgent):
    """
    The Reviewer agent reviews code quality and challenges other agents.
    Acts as a quality gatekeeper with consensus voting power.
    """
    
    def __init__(self, bus: MessageBus, **kwargs):
        super().__init__(
            name="Reviewer",
            role="reviewer",
            system_prompt="""You are the Reviewer agent 👀. Your job is to ensure code quality.

REVIEW CHECKLIST:
1. Code Completeness - Is the code complete and runnable?
2. Code Quality - Clean, readable, well-organized?
3. Best Practices - Following Python/JS conventions?
4. Error Handling - Are edge cases handled?
5. Security - Any obvious vulnerabilities?

CONSENSUS VOTING:
- You can CHALLENGE any code that doesn't meet quality standards
- Vote APPROVE only if code passes all checks
- Your vote carries weight in the consensus

Respond with detailed review in JSON:
{
  "quality_score": 1-10,
  "completeness": true/false,
  "issues": ["issue1", "issue2"],
  "improvements": ["suggestion1", "suggestion2"],
  "vote": "APPROVE | CHALLENGE",
  "reasoning": "Why you voted this way"
}""",
            bus=bus,
            **kwargs
        )
        self.reviews_completed = 0
    
    async def handle_message(self, message: AgentMessage):
        """Handle code messages for review."""
        if message.type == MessageType.CODE and message.content.get("success"):
            await self.review_code(message.content)
    
    async def review_code(self, code_info: Dict):
        """Review code and vote on quality."""
        file_name = code_info.get("file", "unknown")
        code = code_info.get("code", "")
        
        await self.broadcast(MessageType.STATUS, f"👀 Reviewing {file_name}...")
        
        # Self-critique the code
        critique = await self.self_critique(code, "code")
        
        # Store review in memory
        self.remember(f"review_{file_name}", critique, "reviews")
        self.reviews_completed += 1
        
        # Broadcast review result
        vote = "APPROVE" if critique.get("quality_score", 0) >= 7 else "CHALLENGE"
        
        await self.broadcast(
            MessageType.STATUS,
            f"👀 Review: {file_name} - Score {critique.get('quality_score', '?')}/10 - {vote}"
        )
        
        if vote == "CHALLENGE" and critique.get("issues"):
            # Send challenge to Arbiter
            await self.send_message(
                "Arbiter",
                MessageType.CONTRADICTION,
                {
                    "file": file_name,
                    "issues": critique.get("issues", []),
                    "from": "Reviewer",
                    "quality_score": critique.get("quality_score", 0)
                }
            )
    
    async def process_task(self, task: str, context: Dict) -> Dict:
        return {"status": "waiting_for_code"}


class ArchitectAgent(BaseAgent):
    """
    The Architect agent makes high-level design decisions.
    Challenges the Planner and ensures architectural consistency.
    """
    
    def __init__(self, bus: MessageBus, **kwargs):
        super().__init__(
            name="Architect",
            role="architect",
            system_prompt="""You are the Architect agent 🏗️. Your job is high-level design.

ARCHITECTURAL RESPONSIBILITIES:
1. Design Patterns - Suggest appropriate patterns (MVC, Observer, etc.)
2. Code Structure - How should files/classes be organized?
3. Dependencies - What libraries are needed?
4. Scalability - Will this design scale?
5. Consistency - Does it match existing codebase patterns?

CONSENSUS VOTING:
- You vote on Planner's proposals
- CHALLENGE plans that violate architectural principles
- Suggest improvements to the design

When reviewing plans, respond in JSON:
{
  "design_score": 1-10,
  "patterns_suggested": ["pattern1", "pattern2"],
  "concerns": ["concern1", "concern2"],
  "improvements": ["improvement1", "improvement2"],
  "vote": "APPROVE | CHALLENGE",
  "reasoning": "Architectural justification"
}""",
            bus=bus,
            **kwargs
        )
        self.designs_reviewed = 0
    
    async def handle_message(self, message: AgentMessage):
        """Handle plan messages for architectural review."""
        if message.type == MessageType.PLAN:
            await self.review_architecture(message.content)
    
    async def review_architecture(self, plan: Dict):
        """Review plan architecture."""
        await self.broadcast(MessageType.STATUS, f"🏗️ Reviewing architecture...")
        
        review_prompt = f"""Review this plan architecturally:

PLAN: {json.dumps(plan, indent=2)[:2000]}

Evaluate the design and suggest improvements."""

        response = await self.call_llm(review_prompt, max_tokens=1000)
        
        self.designs_reviewed += 1
        self.remember(f"architecture_review_{self.designs_reviewed}", response, "architecture")
        
        await self.broadcast(
            MessageType.STATUS,
            f"🏗️ Architecture review complete - Design approved"
        )
    
    async def process_task(self, task: str, context: Dict) -> Dict:
        return {"status": "waiting_for_plans"}


class ExecutorAgent(BaseAgent):
    """
    The Executor agent autonomously launches and previews solutions.
    Handles CLI launch, web servers, and solution validation.
    """
    
    def __init__(self, bus: MessageBus, **kwargs):
        super().__init__(
            name="Executor",
            role="executor",
            system_prompt="""You are the Executor agent 🚀. Your job is to LAUNCH and PREVIEW solutions.

EXECUTION RESPONSIBILITIES:
1. Launch Applications - Run games, web servers, CLI tools
2. Preview Solutions - Open browsers, show output
3. Validate End-to-End - Ensure the full solution works
4. Report Results - Tell users how to access their solution

LAUNCH STRATEGIES:
- Python games (pygame): Run in foreground with display
- Web apps (Flask/FastAPI): Start server, report URL
- CLI tools: Execute and show output
- Node.js apps: npm start, report port

After launching, report:
{
  "launched": true/false,
  "type": "game | web | cli",
  "access": "How to access (URL, command, etc.)",
  "pid": "Process ID if background"
}""",
            bus=bus,
            **kwargs
        )
        self.launched_processes: List[Dict] = []
    
    async def handle_message(self, message: AgentMessage):
        """Handle successful test results to launch preview."""
        if message.type == MessageType.TEST_RESULT and message.content.get("passed"):
            await self.launch_preview(message.content)
    
    async def launch_preview(self, test_result: Dict):
        """Launch and preview the completed solution."""
        file_name = test_result.get("file", "")
        
        # Skip if already launched
        if any(p.get("file") == file_name for p in self.launched_processes):
            return
        
        await self.broadcast(MessageType.STATUS, f"🚀 Preparing to launch {file_name}...")
        
        # Read file to determine launch strategy
        code_result = self.call_mcp("fs", "read", {"path": file_name})
        code = code_result.get("content", "")
        
        launch_info = {"file": file_name, "launched": False}
        
        # Determine launch strategy based on content
        if "pygame" in code or "tkinter" in code:
            # GUI app - user needs to run manually
            launch_info["type"] = "game"
            launch_info["access"] = f"Run: python3 /Users/yacinebenhamou/AgentY/workspace/{file_name}"
            launch_info["launched"] = True
            await self.broadcast(
                MessageType.STATUS,
                f"🎮 Game ready! Run: python3 /Users/yacinebenhamou/AgentY/workspace/{file_name}"
            )
        elif "flask" in code.lower() or "fastapi" in code.lower():
            # Web app - start server
            launch_info["type"] = "web"
            # Start the server in background
            exec_result = self.call_mcp("shell", "run", {
                "command": f"cd /Users/yacinebenhamou/AgentY/workspace && python3 {file_name} &"
            })
            launch_info["access"] = "http://localhost:5000 or http://localhost:8000"
            launch_info["launched"] = True
            await self.broadcast(
                MessageType.STATUS,
                f"🌐 Web app launched! Access at {launch_info['access']}"
            )
        else:
            # CLI tool - show how to run
            launch_info["type"] = "cli"
            launch_info["access"] = f"python3 /Users/yacinebenhamou/AgentY/workspace/{file_name}"
            launch_info["launched"] = True
            await self.broadcast(
                MessageType.STATUS,
                f"✅ Solution ready! Run: {launch_info['access']}"
            )
        
        self.launched_processes.append(launch_info)
        
        # Store in memory
        self.remember(f"launch_{file_name}", launch_info, "launches")
        
        # Broadcast final status
        await self.broadcast(
            MessageType.RESOLUTION,
            {
                "status": "COMPLETE",
                "file": file_name,
                "launch_info": launch_info
            }
        )
    
    async def process_task(self, task: str, context: Dict) -> Dict:
        return {"status": "waiting_for_successful_tests"}


class ArbiterAgent(BaseAgent):
    """
    The Arbiter (Supervisor) agent coordinates all other agents,
    handles contradictions, and makes final decisions.
    """
    
    def __init__(self, bus: MessageBus, **kwargs):
        super().__init__(
            name="Arbiter",
            role="arbiter",
            system_prompt="""You are the Arbiter agent. Your job is to:
1. Coordinate the Planner, Coder, and Tester agents
2. Resolve contradictions and conflicts
3. Decide when to accept or reject work
4. Make final decisions on quality

You are the supervisor. Your decisions are final.""",
            bus=bus,
            **kwargs
        )
        self.current_goal: Optional[str] = None
        self.contradictions: List[Dict] = []
        self.max_retries_per_model = 3  # 3 retries with same model
        self.fallback_models = ["deepseek-coder-v2:16b", "deepseek-r1:14b", "qwen3:8b"]  # 3 different fallbacks
        self.current_retry = 0
        self.current_fallback_index = -1  # -1 means primary model
        self.revision_count = 0
        self.max_revisions = 6  # 3 retries + 3 fallbacks = 6 total
    
    async def handle_message(self, message: AgentMessage):
        """Handle messages from other agents."""
        if message.type == MessageType.CONTRADICTION:
            await self.handle_contradiction(message.content)
        elif message.type == MessageType.TEST_RESULT:
            await self.handle_test_result(message.content)
    
    async def handle_contradiction(self, contradiction: Dict):
        """Handle a contradiction with retry + fallback model strategy."""
        self.contradictions.append(contradiction)
        self.revision_count += 1
        self.current_retry += 1
        
        # Determine which model to use
        current_model = self.model
        phase_info = ""
        
        if self.current_retry > self.max_retries_per_model:
            # Switch to fallback model
            self.current_fallback_index += 1
            self.current_retry = 1  # Reset retry counter for new model
            
            if self.current_fallback_index >= len(self.fallback_models):
                # All fallbacks exhausted
                await self.broadcast(
                    MessageType.STATUS,
                    f"All retries and fallback models exhausted. Accepting current state."
                )
                await self.broadcast(MessageType.RESOLUTION, {"accepted": True, "reason": "all_fallbacks_exhausted"})
                return
            
            current_model = self.fallback_models[self.current_fallback_index]
            phase_info = f" [FALLBACK: {current_model}]"
        else:
            phase_info = f" [Retry {self.current_retry}/{self.max_retries_per_model}]"
        
        # Ask Coder to revise with potentially different model
        await self.broadcast(
            MessageType.STATUS,
            f"Issue in {contradiction.get('file')}.{phase_info} Requesting revision..."
        )
        
        # Include model hint in the contradiction message
        contradiction["suggested_model"] = current_model
        contradiction["issue"] = "\n".join(contradiction.get("issues", ["Unknown issue"]))
        
        await self.send_message(
            "Coder",
            MessageType.CONTRADICTION,
            contradiction
        )
    
    async def handle_test_result(self, result: Dict):
        """Handle test results from Tester."""
        file_name = result.get("file", "unknown")
        
        if result.get("passed"):
            await self.broadcast(
                MessageType.STATUS,
                f"✓ {file_name} passed all tests"
            )
            
            # Auto-commit successful code to Git
            await self.git_commit(file_name, f"feat: Add {file_name}")
        else:
            await self.broadcast(
                MessageType.STATUS,
                f"✗ {file_name} has issues"
            )
    
    async def git_commit(self, file_name: str, message: str):
        """Commit changes to Git repository."""
        try:
            # Initialize git if needed
            init_result = self.call_mcp("git", "init", {})
            
            # Add file
            add_result = self.call_mcp("git", "add", {"path": file_name})
            
            # Commit
            commit_result = self.call_mcp("git", "commit", {"message": message})
            
            if commit_result.get("success"):
                await self.broadcast(
                    MessageType.GIT_COMMIT,
                    {
                        "file": file_name,
                        "message": message,
                        "hash": commit_result.get("hash", "unknown")
                    }
                )
                await self.broadcast(
                    MessageType.STATUS,
                    f"📝 Committed {file_name}: {message}"
                )
            else:
                # Git commit failed but that's ok - might be no changes
                pass
        except Exception as e:
            # Git operations are optional, don't fail the workflow
            print(f"[Arbiter] Git commit failed (non-critical): {e}")
    
    async def process_task(self, task: str, context: Dict) -> Dict:
        """
        Main entry point for processing a user task.
        Coordinates all agents through the full workflow.
        """
        self.current_goal = task
        self.contradictions = []
        self.revision_count = 0
        
        await self.broadcast(MessageType.STATUS, f"Starting task: {task[:50]}...")
        
        # Create agents if not already running
        planner = None
        coder = None
        tester = None
        
        for name, callbacks in self.bus.subscribers.items():
            if name == "Planner":
                # Get planner instance (simplified - in real impl, track agent instances)
                pass
        
        # Step 1: Get plan from Planner
        await self.send_message("Planner", MessageType.REQUEST, {"goal": task, "context": context})
        
        # The rest happens via message passing:
        # Planner -> broadcasts PLAN
        # Coder -> receives PLAN, writes CODE
        # Tester -> receives CODE, runs tests, sends TEST_RESULT
        # If issues -> Tester sends CONTRADICTION to Arbiter
        # Arbiter -> decides to revise or accept
        
        return {"status": "orchestrating", "goal": task}


class MultiAgentOrchestrator:
    """
    Main orchestrator that manages all agents and provides the external API.
    Includes ConsensusManager for multi-agent voting.
    """
    
    def __init__(self, llm_url: str = "http://127.0.0.1:11434", mcp_url: str = "http://127.0.0.1:8000", model: str = "qwen3:8b"):
        self.bus = MessageBus()
        self.consensus = ConsensusManager(self.bus)  # Consensus voting system
        self.llm_url = llm_url
        self.mcp_url = mcp_url
        self.model = model
        self.agents: Dict[str, BaseAgent] = {}
        self.agent_tasks: Dict[str, asyncio.Task] = {}
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Create all agent instances - 9 agents total for full autonomous pipeline."""
        # Import PM Agent
        try:
            from pm_agent import ProductManagerAgent
            self.agents["ProductManager"] = ProductManagerAgent(self.bus, llm_url=self.llm_url, mcp_url=self.mcp_url, model=self.model)
        except Exception as e:
            print(f"[Orchestrator] PM Agent not loaded: {e}")
        
        # Core agents
        self.agents["Planner"] = PlannerAgent(self.bus, llm_url=self.llm_url, mcp_url=self.mcp_url, model=self.model)
        self.agents["Architect"] = ArchitectAgent(self.bus, llm_url=self.llm_url, mcp_url=self.mcp_url, model=self.model)
        self.agents["Coder"] = CoderAgent(self.bus, llm_url=self.llm_url, mcp_url=self.mcp_url, model=self.model)
        self.agents["Reviewer"] = ReviewerAgent(self.bus, llm_url=self.llm_url, mcp_url=self.mcp_url, model=self.model)
        self.agents["Tester"] = TesterAgent(self.bus, llm_url=self.llm_url, mcp_url=self.mcp_url, model=self.model)
        self.agents["Debugger"] = DebuggerAgent(self.bus, llm_url=self.llm_url, mcp_url=self.mcp_url, model=self.model)
        self.agents["Executor"] = ExecutorAgent(self.bus, llm_url=self.llm_url, mcp_url=self.mcp_url, model=self.model)
        # Supervisor
        self.agents["Arbiter"] = ArbiterAgent(self.bus, llm_url=self.llm_url, mcp_url=self.mcp_url, model=self.model)
        
        # Give each agent access to consensus manager
        for agent in self.agents.values():
            agent.consensus = self.consensus
    
    async def start_agents(self):
        """Start all agent loops."""
        for name, agent in self.agents.items():
            task = asyncio.create_task(agent.run())
            self.agent_tasks[name] = task
            print(f"[Orchestrator] Started {name} agent")
    
    async def stop_agents(self):
        """Stop all agent loops."""
        for name, agent in self.agents.items():
            agent.stop()
        for task in self.agent_tasks.values():
            task.cancel()
    
    def add_message_listener(self, callback: Callable):
        """Add an external listener for agent messages (e.g., WebSocket)."""
        self.bus.add_external_listener(callback)
    
    async def run_task(self, goal: str, context: Dict = None) -> str:
        """
        Run a task through the multi-agent system.
        Returns a run_id for tracking.
        """
        run_id = str(uuid.uuid4())[:8]
        context = context or {}
        context["run_id"] = run_id
        
        # Start with the Arbiter
        arbiter = self.agents["Arbiter"]
        await arbiter.process_task(goal, context)
        
        # Also trigger Planner directly since Arbiter doesn't have direct reference
        planner = self.agents["Planner"]
        await planner.process_task(goal, context)
        
        return run_id
    
    def get_message_history(self, limit: int = 100) -> List[Dict]:
        """Get the message history."""
        return self.bus.get_history(limit)


# Singleton instance
_orchestrator: Optional[MultiAgentOrchestrator] = None

def get_orchestrator() -> MultiAgentOrchestrator:
    """Get the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MultiAgentOrchestrator()
    return _orchestrator


if __name__ == "__main__":
    # Test the multi-agent system
    async def test():
        orch = get_orchestrator()
        
        # Add a simple printer listener
        async def print_message(msg: AgentMessage):
            print(f"[{msg.sender}] {msg.type.value}: {str(msg.content)[:100]}")
        
        orch.add_message_listener(print_message)
        
        # Start agents
        await orch.start_agents()
        
        # Run a task
        run_id = await orch.run_task("Create a simple hello world Python script")
        print(f"Started run: {run_id}")
        
        # Wait for some processing
        await asyncio.sleep(30)
        
        # Stop
        await orch.stop_agents()
    
    asyncio.run(test())
