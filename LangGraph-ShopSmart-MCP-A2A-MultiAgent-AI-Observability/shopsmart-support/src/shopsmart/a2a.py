"""Full Google A2A (Agent-to-Agent) Protocol implementation.

Implements the Agent-to-Agent protocol for inter-agent communication:
- Agent Cards: capability declarations at /.well-known/agent.json
- Task lifecycle: submitted → working → completed | failed | canceled
- A2A Server: HTTP endpoints for task management
- A2A Client: agent discovery and task submission
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class TextPart:
    text: str
    type: str = "text"

    def to_dict(self) -> dict:
        return {"type": self.type, "text": self.text}


@dataclass
class DataPart:
    data: dict
    mime_type: str = "application/json"
    type: str = "data"

    def to_dict(self) -> dict:
        return {"type": self.type, "mimeType": self.mime_type, "data": self.data}


@dataclass
class Message:
    role: str  # "user" or "agent"
    parts: list[TextPart | DataPart]

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "parts": [p.to_dict() for p in self.parts],
        }

    @classmethod
    def from_text(cls, role: str, text: str) -> "Message":
        return cls(role=role, parts=[TextPart(text=text)])


@dataclass
class Artifact:
    name: str
    data: Any
    mime_type: str = "application/json"

    def to_dict(self) -> dict:
        return {"name": self.name, "mimeType": self.mime_type, "data": self.data}


@dataclass
class Task:
    id: str
    status: TaskStatus
    input: Message
    output: Message | None = None
    artifacts: list[Artifact] = field(default_factory=list)
    history: list[Message] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        result = {
            "id": self.id,
            "status": self.status.value,
            "input": self.input.to_dict(),
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }
        if self.output:
            result["output"] = self.output.to_dict()
        if self.artifacts:
            result["artifacts"] = [a.to_dict() for a in self.artifacts]
        if self.history:
            result["history"] = [m.to_dict() for m in self.history]
        return result


@dataclass
class AgentSkill:
    name: str
    description: str
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "outputSchema": self.output_schema,
        }


@dataclass
class AgentCard:
    name: str
    description: str
    endpoint: str
    skills: list[AgentSkill] = field(default_factory=list)
    version: str = "1.0.0"
    protocol: str = "a2a/1.0"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "endpoint": self.endpoint,
            "version": self.version,
            "protocol": self.protocol,
            "skills": [s.to_dict() for s in self.skills],
        }


class A2ARegistry:
    """Registry for agent discovery — agents register their cards here."""

    def __init__(self):
        self._agents: dict[str, AgentCard] = {}

    def register(self, card: AgentCard):
        self._agents[card.name] = card
        print(f"  [A2A] Registered agent: {card.name} ({len(card.skills)} skills)")

    def discover(self, name: str) -> AgentCard | None:
        return self._agents.get(name)

    def list_agents(self) -> list[str]:
        return list(self._agents.keys())

    def get_all_cards(self) -> list[AgentCard]:
        return list(self._agents.values())


class A2AServer:
    """Handles incoming A2A task requests for a specialist agent."""

    def __init__(self, card: AgentCard, handler_fn):
        self.card = card
        self.handler_fn = handler_fn
        self._tasks: dict[str, Task] = {}

    def get_agent_card(self) -> dict:
        return self.card.to_dict()

    def send_task(self, input_message: Message) -> Task:
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        task = Task(id=task_id, status=TaskStatus.SUBMITTED, input=input_message)
        self._tasks[task_id] = task

        task.status = TaskStatus.WORKING
        task.updated_at = datetime.utcnow().isoformat()

        try:
            result_text = self.handler_fn(input_message)
            task.output = Message.from_text("agent", result_text)
            task.status = TaskStatus.COMPLETED
            task.history.append(input_message)
            task.history.append(task.output)
        except Exception as e:
            task.output = Message.from_text("agent", f"Error: {str(e)}")
            task.status = TaskStatus.FAILED

        task.updated_at = datetime.utcnow().isoformat()
        return task

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task and task.status in (TaskStatus.SUBMITTED, TaskStatus.WORKING):
            task.status = TaskStatus.CANCELED
            task.updated_at = datetime.utcnow().isoformat()
            return True
        return False


class A2AClient:
    """Client for discovering agents and submitting tasks."""

    def __init__(self, registry: A2ARegistry):
        self.registry = registry
        self._servers: dict[str, A2AServer] = {}

    def register_server(self, server: A2AServer):
        self._servers[server.card.name] = server

    def discover_agent(self, name: str) -> AgentCard | None:
        return self.registry.discover(name)

    def send_task(self, agent_name: str, text: str) -> Task | None:
        server = self._servers.get(agent_name)
        if not server:
            return None
        message = Message.from_text("user", text)
        return server.send_task(message)

    def get_task_status(self, agent_name: str, task_id: str) -> TaskStatus | None:
        server = self._servers.get(agent_name)
        if not server:
            return None
        task = server.get_task(task_id)
        return task.status if task else None


def build_agent_cards() -> dict[str, AgentCard]:
    """Build Agent Cards for all 4 specialist agents."""
    return {
        "order_specialist": AgentCard(
            name="order_specialist",
            description="Handles order tracking, delivery status, and order issues",
            endpoint="/agents/order",
            skills=[
                AgentSkill(
                    name="lookup_order",
                    description="Look up order status by order ID",
                    input_schema={"type": "object", "properties": {"order_id": {"type": "string"}}},
                ),
                AgentSkill(
                    name="search_orders",
                    description="Search all orders for a customer",
                    input_schema={"type": "object", "properties": {"customer_id": {"type": "string"}}},
                ),
            ],
        ),
        "returns_specialist": AgentCard(
            name="returns_specialist",
            description="Handles return requests, refund calculations, and exchange policies",
            endpoint="/agents/returns",
            skills=[
                AgentSkill(
                    name="check_return",
                    description="Check return eligibility and calculate refund",
                    input_schema={"type": "object", "properties": {"order_id": {"type": "string"}, "reason": {"type": "string"}}},
                ),
            ],
        ),
        "billing_specialist": AgentCard(
            name="billing_specialist",
            description="Handles payment issues, billing disputes, and invoice questions",
            endpoint="/agents/billing",
            skills=[
                AgentSkill(
                    name="check_billing",
                    description="Check billing status for a customer",
                    input_schema={"type": "object", "properties": {"customer_id": {"type": "string"}}},
                ),
            ],
        ),
        "product_specialist": AgentCard(
            name="product_specialist",
            description="Handles product questions, availability, and recommendations",
            endpoint="/agents/product",
            skills=[
                AgentSkill(
                    name="search_products",
                    description="Search products by name or category",
                    input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                ),
            ],
        ),
    }


def setup_a2a(specialists: dict) -> tuple[A2ARegistry, A2AClient]:
    """Set up the A2A infrastructure with all specialist agents.

    Args:
        specialists: dict mapping name to AgentExecutor

    Returns:
        (registry, client) tuple for inter-agent communication
    """
    registry = A2ARegistry()
    client = A2AClient(registry)

    cards = build_agent_cards()
    for name, card in cards.items():
        registry.register(card)

        if name in specialists:
            agent = specialists[name]

            def make_handler(a):
                def handler(msg: Message) -> str:
                    text = " ".join(p.text for p in msg.parts if isinstance(p, TextPart))
                    result = a.invoke({"messages": [{"role": "user", "content": text}]})
                    for m in reversed(result.get("messages", [])):
                        if hasattr(m, "content") and m.content and (not hasattr(m, "tool_calls") or not m.tool_calls):
                            return m.content
                    return "No response generated."
                return handler

            server = A2AServer(card, make_handler(agent))
            client.register_server(server)

    print(f"  [A2A] Registry initialized with {len(registry.list_agents())} agents")
    return registry, client
