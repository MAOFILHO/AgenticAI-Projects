"""
state.py — Shared state and Pydantic classification schema.
"""
from typing import Annotated, Literal, TypedDict

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class CustomerSupportState(TypedDict):
    """
    Shared state that flows through every node in the multi-agent graph.

    Fields
    ------
    messages                  Conversation history (add_messages reducer).
    ticket_id                 Source ticket identifier.
    customer_id               ShopSmart customer ID (CUST-XXXX).
    customer_tier             bronze / silver / platinum.
    ticket_text               Original text with PII — NEVER sent to any LLM.
    redacted_text             PII-scrubbed text — the only version LLMs see.
    category                  LLM classification: order_status / returns / billing /
                              product_inquiry / technical / escalation.
    priority                  low / medium / high / critical.
    classification_confidence Float 0-1 from the supervisor classifier.
    specialist_response       Raw response from whichever specialist handled this.
    needs_escalation          True → route to HITL node.
    human_notes               Manager notes injected via Command(resume=…).
    final_response            Formatted customer-facing response.
    tools_used                Ordered list of every tool/node called (observability).
    pii_mapping               Placeholder→original mapping for PII restoration.
    """

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
    """
    Structured output schema for the supervisor's LLM classifier.

    Using Pydantic structured output eliminates JSON-parsing errors and
    guarantees the router always receives a valid routing decision.
    """

    category: Literal[
        "order_status",
        "returns",
        "billing",
        "product_inquiry",
        "technical",
        "escalation",
    ] = Field(description="Primary category of the support ticket.")

    priority: Literal["low", "medium", "high", "critical"] = Field(
        description="Priority level based on urgency and customer tier."
    )

    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0 for this classification.",
        ge=0.0,
        le=1.0,
    )

    requires_escalation: bool = Field(
        description=(
            "True if the ticket should be escalated to a human manager. "
            "Escalate when: (1) customer explicitly requests a manager, "
            "(2) ticket mentions legal action or social-media threats, "
            "(3) category is 'escalation', or "
            "(4) issue involves a dispute over $500."
        )
    )

    reasoning: str = Field(
        description="Brief explanation of why this category and priority were chosen."
    )
