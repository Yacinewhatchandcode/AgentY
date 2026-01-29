"""
Product Manager Agent for AgentY
=================================
Transforms raw ideas into perfect, machine-readable technical specifications.
After this agent finishes, Coder Agents need no interpretation or clarification.

Mission: Be the SINGLE SOURCE OF TRUTH for what must be built.
"""

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

from agents import BaseAgent, MessageBus, MessageType, AgentMessage


class Priority(Enum):
    P0 = "P0"  # Must have - MVP
    P1 = "P1"  # Should have
    P2 = "P2"  # Nice to have
    P3 = "P3"  # Future


class Scope(Enum):
    MVP = "MVP"
    V1 = "V1"
    V2 = "V2"
    FUTURE = "Future"


@dataclass
class Vision:
    """Product vision document."""
    product_name: str
    problem_statement: str
    target_users: List[str]
    value_proposition: str
    non_goals: List[str]
    success_metrics: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return {
            "product_name": self.product_name,
            "problem_statement": self.problem_statement,
            "target_users": self.target_users,
            "value_proposition": self.value_proposition,
            "non_goals": self.non_goals,
            "success_metrics": self.success_metrics
        }


@dataclass
class Feature:
    """Feature definition."""
    feature_id: str
    name: str
    description: str
    business_value: str  # High, Medium, Low
    priority: Priority
    scope: Scope
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "feature_id": self.feature_id,
            "name": self.name,
            "description": self.description,
            "business_value": self.business_value,
            "priority": self.priority.value,
            "scope": self.scope.value,
            "dependencies": self.dependencies
        }


@dataclass
class UserStory:
    """User story with acceptance criteria."""
    story_id: str
    feature_id: str
    as_a: str
    i_want: str
    so_that: str
    acceptance_criteria: List[str]
    priority: Priority
    
    def to_dict(self) -> Dict:
        return {
            "story_id": self.story_id,
            "feature_id": self.feature_id,
            "as_a": self.as_a,
            "i_want": self.i_want,
            "so_that": self.so_that,
            "acceptance_criteria": self.acceptance_criteria,
            "priority": self.priority.value
        }


@dataclass
class Task:
    """Atomic task for Coder Agents."""
    task_id: str
    story_id: str
    title: str
    description: str
    tech_stack: str
    dependencies: List[str]
    acceptance_criteria: List[str]
    estimated_complexity: str  # XS, S, M, L, XL
    coder_prompt: str
    
    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "story_id": self.story_id,
            "title": self.title,
            "description": self.description,
            "tech_stack": self.tech_stack,
            "dependencies": self.dependencies,
            "acceptance_criteria": self.acceptance_criteria,
            "estimated_complexity": self.estimated_complexity,
            "coder_prompt": self.coder_prompt
        }
    
    def to_csv_row(self) -> str:
        deps = "|".join(self.dependencies) if self.dependencies else "None"
        return f"{self.task_id},{self.title},{self.tech_stack},{deps},{self.estimated_complexity}"


@dataclass
class SpecPackage:
    """Complete specification package."""
    spec_id: str
    vision: Vision
    features: List[Feature]
    stories: List[UserStory]
    tasks: List[Task]
    data_model: Dict
    nfr: Dict
    openapi: Dict
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def save_to_directory(self, base_path: Path):
        """Save all artifacts to a directory."""
        spec_dir = base_path / self.spec_id
        spec_dir.mkdir(parents=True, exist_ok=True)
        
        # vision.json
        with open(spec_dir / "vision.json", "w") as f:
            json.dump(self.vision.to_dict(), f, indent=2)
        
        # features.json
        with open(spec_dir / "features.json", "w") as f:
            json.dump([f.to_dict() for f in self.features], f, indent=2)
        
        # stories.json
        with open(spec_dir / "stories.json", "w") as f:
            json.dump({"stories": [s.to_dict() for s in self.stories]}, f, indent=2)
        
        # tasks.json + tasks.csv
        with open(spec_dir / "tasks.json", "w") as f:
            json.dump([t.to_dict() for t in self.tasks], f, indent=2)
        
        with open(spec_dir / "tasks.csv", "w") as f:
            f.write("task_id,title,tech_stack,dependencies,complexity\n")
            for task in self.tasks:
                f.write(task.to_csv_row() + "\n")
        
        # data_model.json
        with open(spec_dir / "data_model.json", "w") as f:
            json.dump(self.data_model, f, indent=2)
        
        # nfr.json
        with open(spec_dir / "nfr.json", "w") as f:
            json.dump(self.nfr, f, indent=2)
        
        # openapi.yaml (as json for now)
        with open(spec_dir / "openapi.json", "w") as f:
            json.dump(self.openapi, f, indent=2)
        
        # prompts_for_coder.json
        coder_prompts = {t.task_id: t.coder_prompt for t in self.tasks}
        with open(spec_dir / "prompts_for_coder.json", "w") as f:
            json.dump(coder_prompts, f, indent=2)
        
        print(f"[PM Agent] Saved spec package to {spec_dir}")
        return spec_dir


class ProductManagerAgent(BaseAgent):
    """
    Product Manager Agent - Transforms ideas into executable specifications.
    
    This agent is accountable for:
    - Clarity: No ambiguous requirements
    - Precision: All edge cases defined
    - Executability: Coder agents can work without clarification
    
    Key Principle: If a Coder Agent fails, the PM Agent spec was insufficient.
    """
    
    def __init__(
        self,
        bus: MessageBus,
        llm_url: str = "http://127.0.0.1:11434",
        mcp_url: str = "http://127.0.0.1:8000",
        model: str = "qwen3:8b"
    ):
        system_prompt = """You are a Product Manager Agent. Your mission is to transform raw ideas into
PERFECT, UNAMBIGUOUS, MACHINE-READABLE technical specifications.

Your outputs must be:
1. DETERMINISTIC - Same input always produces consistent output
2. VERSIONED - Every artifact has a unique ID
3. MACHINE-READABLE - JSON, not prose
4. COMPLETE - No placeholders, no "TBD"
5. ATOMIC - Each task is independently implementable

If you cannot fully specify something, you MUST:
- Generate clarification questions
- Block downstream execution
- Never pass ambiguity downstream

You are the SINGLE SOURCE OF TRUTH for what must be built.
After you finish, Coder Agents should need NO interpretation."""

        super().__init__(
            name="ProductManager",
            role="pm",
            system_prompt=system_prompt,
            bus=bus,
            llm_url=llm_url,
            mcp_url=mcp_url,
            model=model
        )
        
        self.current_spec: Optional[SpecPackage] = None
        self.specs_dir = Path.home() / ".agenty" / "specs"
        self.specs_dir.mkdir(parents=True, exist_ok=True)
    
    async def process_task(self, task: str, context: Dict) -> Any:
        """Process an idea and generate complete specifications."""
        print(f"[PM Agent] Processing idea: {task[:100]}...")
        
        # Generate all spec components
        vision = await self._generate_vision(task, context)
        features = await self._generate_features(task, vision, context)
        stories = await self._generate_stories(features, context)
        data_model = await self._generate_data_model(features, stories, context)
        nfr = await self._generate_nfr(context)
        openapi = await self._generate_openapi(features, stories, data_model, context)
        tasks = await self._generate_tasks(stories, openapi, context)
        
        # Create spec package
        spec_id = f"spec-{uuid.uuid4().hex[:8]}"
        self.current_spec = SpecPackage(
            spec_id=spec_id,
            vision=vision,
            features=features,
            stories=stories,
            tasks=tasks,
            data_model=data_model,
            nfr=nfr,
            openapi=openapi
        )
        
        # Validate spec quality
        quality_report = self._validate_spec_quality()
        if not quality_report["passed"]:
            await self.broadcast(MessageType.STATUS, {
                "agent": "ProductManager",
                "status": "blocked",
                "reason": "Spec quality gate failed",
                "issues": quality_report["issues"]
            })
            return {"status": "blocked", "issues": quality_report["issues"]}
        
        # Save to disk
        spec_path = self.current_spec.save_to_directory(self.specs_dir)
        
        # Log decision to graph memory
        self.log_decision(
            action="spec_generated",
            content={
                "spec_id": spec_id,
                "features_count": len(features),
                "stories_count": len(stories),
                "tasks_count": len(tasks),
                "quality_score": quality_report["score"]
            },
            run_id=context.get("run_id", "default")
        )
        
        # Broadcast completion
        await self.broadcast(MessageType.STATUS, {
            "agent": "ProductManager",
            "status": "completed",
            "spec_id": spec_id,
            "spec_path": str(spec_path),
            "summary": {
                "features": len(features),
                "stories": len(stories),
                "tasks": len(tasks),
                "quality_score": quality_report["score"]
            }
        })
        
        return {
            "status": "completed",
            "spec_id": spec_id,
            "spec_path": str(spec_path),
            "tasks": [t.to_dict() for t in tasks]
        }
    
    async def _generate_vision(self, idea: str, context: Dict) -> Vision:
        """Generate product vision."""
        prompt = f"""Analyze this idea and create a product vision.

IDEA: {idea}

Respond with ONLY valid JSON (no explanation):
{{
  "product_name": "short name",
  "problem_statement": "clear problem being solved",
  "target_users": ["user type 1", "user type 2"],
  "value_proposition": "why this matters",
  "non_goals": ["what we explicitly won't do"],
  "success_metrics": {{
    "primary": "main KPI",
    "secondary": ["other metrics"]
  }}
}}"""
        
        response = await self._call_llm(prompt, max_tokens=1024)
        
        try:
            # Extract JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                return Vision(
                    product_name=data.get("product_name", "Untitled"),
                    problem_statement=data.get("problem_statement", ""),
                    target_users=data.get("target_users", []),
                    value_proposition=data.get("value_proposition", ""),
                    non_goals=data.get("non_goals", []),
                    success_metrics=data.get("success_metrics", {})
                )
        except Exception as e:
            print(f"[PM Agent] Vision parse error: {e}")
        
        # Fallback
        return Vision(
            product_name=idea[:30],
            problem_statement=idea,
            target_users=["end users"],
            value_proposition="Solve the stated problem",
            non_goals=[],
            success_metrics={"primary": "user satisfaction"}
        )
    
    async def _generate_features(self, idea: str, vision: Vision, context: Dict) -> List[Feature]:
        """Generate feature list."""
        prompt = f"""Based on this product vision, list the MVP features.

VISION:
{json.dumps(vision.to_dict(), indent=2)}

Respond with ONLY valid JSON array:
[
  {{
    "feature_id": "F-001",
    "name": "Feature Name",
    "description": "What it does",
    "business_value": "High|Medium|Low",
    "priority": "P0|P1|P2",
    "scope": "MVP|V1|V2",
    "dependencies": []
  }}
]

Generate 3-6 features for MVP."""
        
        response = await self._call_llm(prompt, max_tokens=2048)
        
        features = []
        try:
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                data = json.loads(json_match.group())
                for i, f in enumerate(data):
                    features.append(Feature(
                        feature_id=f.get("feature_id", f"F-{i+1:03d}"),
                        name=f.get("name", f"Feature {i+1}"),
                        description=f.get("description", ""),
                        business_value=f.get("business_value", "Medium"),
                        priority=Priority(f.get("priority", "P1")),
                        scope=Scope(f.get("scope", "MVP")),
                        dependencies=f.get("dependencies", [])
                    ))
        except Exception as e:
            print(f"[PM Agent] Features parse error: {e}")
            features = [Feature(
                feature_id="F-001",
                name="Core Functionality",
                description=vision.problem_statement,
                business_value="High",
                priority=Priority.P0,
                scope=Scope.MVP
            )]
        
        return features
    
    async def _generate_stories(self, features: List[Feature], context: Dict) -> List[UserStory]:
        """Generate user stories with acceptance criteria."""
        stories = []
        
        for feature in features:
            prompt = f"""Create user stories for this feature:

FEATURE: {feature.name}
DESCRIPTION: {feature.description}

Respond with ONLY valid JSON array:
[
  {{
    "story_id": "S-001",
    "as_a": "user type",
    "i_want": "action",
    "so_that": "benefit",
    "acceptance_criteria": [
      "GIVEN X WHEN Y THEN Z",
      "API returns 200 on success",
      "Unit tests cover success and failure"
    ]
  }}
]

Generate 1-3 stories per feature. Acceptance criteria must be TESTABLE."""
            
            response = await self._call_llm(prompt, max_tokens=2048)
            
            try:
                json_match = re.search(r'\[[\s\S]*\]', response)
                if json_match:
                    data = json.loads(json_match.group())
                    for s in data:
                        story_id = f"S-{len(stories)+1:03d}"
                        stories.append(UserStory(
                            story_id=story_id,
                            feature_id=feature.feature_id,
                            as_a=s.get("as_a", "user"),
                            i_want=s.get("i_want", ""),
                            so_that=s.get("so_that", ""),
                            acceptance_criteria=s.get("acceptance_criteria", []),
                            priority=feature.priority
                        ))
            except Exception as e:
                print(f"[PM Agent] Stories parse error: {e}")
        
        return stories
    
    async def _generate_data_model(self, features: List[Feature], stories: List[UserStory], context: Dict) -> Dict:
        """Generate data model."""
        feature_names = [f.name for f in features]
        
        prompt = f"""Create a data model for these features: {feature_names}

Respond with ONLY valid JSON:
{{
  "entities": {{
    "EntityName": {{
      "field_name": "type (constraints)"
    }}
  }},
  "relationships": [
    "Entity1 has_many Entity2"
  ]
}}"""
        
        response = await self._call_llm(prompt, max_tokens=1024)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {"entities": {}, "relationships": []}
    
    async def _generate_nfr(self, context: Dict) -> Dict:
        """Generate non-functional requirements."""
        return {
            "performance": {
                "p95_latency_ms": 200,
                "max_concurrent_users": 100
            },
            "security": {
                "authentication": "required",
                "authorization": "role-based",
                "data_encryption": "at-rest and in-transit"
            },
            "reliability": {
                "uptime_target": "99.9%",
                "error_rate_threshold": "0.1%"
            },
            "maintainability": {
                "code_coverage_min": "80%",
                "documentation_required": True
            }
        }
    
    async def _generate_openapi(self, features: List[Feature], stories: List[UserStory], data_model: Dict, context: Dict) -> Dict:
        """Generate OpenAPI specification."""
        prompt = f"""Create an OpenAPI 3.0 specification for these features:
{[f.name for f in features]}

Data model entities: {list(data_model.get('entities', {}).keys())}

Respond with ONLY valid JSON (OpenAPI 3.0 format):
{{
  "openapi": "3.0.0",
  "info": {{"title": "API", "version": "1.0.0"}},
  "paths": {{
    "/endpoint": {{
      "get": {{"summary": "...", "responses": {{"200": {{"description": "..."}}}}}}
    }}
  }}
}}"""
        
        response = await self._call_llm(prompt, max_tokens=3000)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {}
        }
    
    async def _generate_tasks(self, stories: List[UserStory], openapi: Dict, context: Dict) -> List[Task]:
        """Generate atomic tasks for Coder Agents."""
        tasks = []
        
        for story in stories:
            prompt = f"""Break down this user story into ATOMIC coding tasks:

STORY: As a {story.as_a}, I want {story.i_want} so that {story.so_that}

ACCEPTANCE CRITERIA:
{chr(10).join(f'- {ac}' for ac in story.acceptance_criteria)}

Respond with ONLY valid JSON array:
[
  {{
    "title": "Implement X",
    "description": "Detailed description",
    "tech_stack": "FastAPI/Python",
    "dependencies": [],
    "estimated_complexity": "S|M|L",
    "acceptance_criteria": ["testable criterion"]
  }}
]

Each task must be:
- ATOMIC (1-2 hours of work)
- INDEPENDENTLY TESTABLE
- NO AMBIGUITY"""
            
            response = await self._call_llm(prompt, max_tokens=2048)
            
            try:
                json_match = re.search(r'\[[\s\S]*\]', response)
                if json_match:
                    data = json.loads(json_match.group())
                    for t in data:
                        task_id = f"T-{len(tasks)+1:03d}"
                        
                        # Generate coder prompt
                        coder_prompt = f"""You are a Coder Agent. Implement this task:

TASK: {t.get('title', '')}
DESCRIPTION: {t.get('description', '')}
TECH STACK: {t.get('tech_stack', 'Python')}

ACCEPTANCE CRITERIA:
{chr(10).join(f'- {ac}' for ac in t.get('acceptance_criteria', []))}

Requirements:
1. Follow the existing code style
2. Include type hints
3. Write unit tests
4. Return a complete implementation

Do NOT ask for clarification. All information is provided."""
                        
                        tasks.append(Task(
                            task_id=task_id,
                            story_id=story.story_id,
                            title=t.get("title", f"Task {len(tasks)+1}"),
                            description=t.get("description", ""),
                            tech_stack=t.get("tech_stack", "Python"),
                            dependencies=t.get("dependencies", []),
                            acceptance_criteria=t.get("acceptance_criteria", []),
                            estimated_complexity=t.get("estimated_complexity", "M"),
                            coder_prompt=coder_prompt
                        ))
            except Exception as e:
                print(f"[PM Agent] Tasks parse error: {e}")
        
        return tasks
    
    def _validate_spec_quality(self) -> Dict:
        """Validate spec quality - blocks downstream if insufficient."""
        if not self.current_spec:
            return {"passed": False, "score": 0, "issues": ["No spec generated"]}
        
        issues = []
        score = 100
        
        # Check vision completeness
        if not self.current_spec.vision.problem_statement:
            issues.append("Missing problem statement")
            score -= 20
        
        # Check features
        if len(self.current_spec.features) == 0:
            issues.append("No features defined")
            score -= 30
        
        # Check stories have acceptance criteria
        for story in self.current_spec.stories:
            if len(story.acceptance_criteria) < 2:
                issues.append(f"{story.story_id}: Insufficient acceptance criteria")
                score -= 5
        
        # Check tasks are atomic
        for task in self.current_spec.tasks:
            if task.estimated_complexity in ["XL", "XXL"]:
                issues.append(f"{task.task_id}: Too complex, needs breakdown")
                score -= 10
            if not task.coder_prompt:
                issues.append(f"{task.task_id}: Missing coder prompt")
                score -= 5
        
        # Check OpenAPI
        if not self.current_spec.openapi.get("paths"):
            issues.append("OpenAPI has no paths defined")
            score -= 15
        
        passed = score >= 70 and len([i for i in issues if "Missing" in i or "No " in i]) == 0
        
        return {
            "passed": passed,
            "score": max(0, score),
            "issues": issues
        }
    
    def get_tasks_for_coder(self) -> List[Dict]:
        """Get tasks formatted for Coder Agents."""
        if not self.current_spec:
            return []
        return [t.to_dict() for t in self.current_spec.tasks]
    
    def get_coder_prompts(self) -> Dict[str, str]:
        """Get prompts for Coder Agents."""
        if not self.current_spec:
            return {}
        return {t.task_id: t.coder_prompt for t in self.current_spec.tasks}


# ==================== FACTORY ====================

def create_pm_agent(bus: MessageBus, **kwargs) -> ProductManagerAgent:
    """Factory function to create a PM Agent."""
    return ProductManagerAgent(bus, **kwargs)
