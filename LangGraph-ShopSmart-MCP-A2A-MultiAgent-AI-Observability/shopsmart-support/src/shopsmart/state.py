"""State schema and Pydantic classification model."""

from typing import Annotated, Literal, TypedDict

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class CustomerSupportState(TypedDict):
    """Shared state flowing through every node in the graph."""

    messages: Annotated[list, add_messages]

    ticket_id: str
    customer_id: str
    customer_tier: str

    ticket_text: str
    redacted_text: str

    category: str
    priority: str
    classification_confidence: float

    specialist_response: str
    needs_escalation: bool
    human_notes: str

    final_response: str

    tools_used: list[str]
    pii_mapping: dict


class TicketClassification(BaseModel):
    """Structured output for ticket classification by the supervisor."""

    category: Literal[
        "order_status",
        "returns",
        "billing",
        "product_inquiry",
        "technical",
        "escalation",
    ] = Field(description="The primary category of the support ticket")

    priority: Literal["low", "medium", "high", "critical"] = Field(
        description="Priority level based on urgency and customer tier"
    )

    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0",
        ge=0.0,
        le=1.0,
    )

    requires_escalation: bool = Field(
        description=(
            "True if the ticket should be escalated to a human manager. "
            "Escalate when: (1) customer explicitly requests a manager, "
            "(2) ticket mentions legal action or social media threats, "
            "(3) category is 'escalation', or "
            "(4) issue involves a high-value dispute over $500."
        )
    )

    reasoning: str = Field(
        description="Brief explanation of why this category and priority were chosen"
    )
