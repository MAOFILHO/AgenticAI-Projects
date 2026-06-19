"""ShopSmart support agent — Spine A LangGraph implementation."""

import json
from typing import Literal, TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from data import BILLING_POLICY, ORDERS_DB, RETURN_POLICY

llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.3)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    customer_query: str
    category: str
    response: str


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

class RouteDecision(BaseModel):
    category: Literal["order_status", "returns", "billing", "product_info"] = Field(
        description="Customer query category"
    )


def classify_query(state: AgentState) -> dict:
    decision = llm.with_structured_output(RouteDecision).invoke(
        f"Classify into one category: order_status, returns, billing, product_info.\n"
        f"Query: {state['customer_query']}"
    )
    return {"category": decision.category}


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

order_prompt = ChatPromptTemplate.from_template(
    "You are ShopSmart's order specialist.\n"
    "Orders: {orders}\n"
    "Query: {query}\n"
    "Provide a 2-3 sentence helpful response."
)
returns_prompt = ChatPromptTemplate.from_template(
    "You are ShopSmart's returns specialist.\n"
    "Policy: {policy}\n"
    "Query: {query}\n"
    "Provide a 2-3 sentence response."
)
billing_prompt = ChatPromptTemplate.from_template(
    "You are ShopSmart's billing specialist.\n"
    "Policy: {policy}\n"
    "Query: {query}\n"
    "Provide a 2-3 sentence response."
)
product_prompt = ChatPromptTemplate.from_template(
    "You are ShopSmart's product specialist.\n"
    "Products: {orders}\n"
    "Query: {query}\n"
    "Provide a 2-3 sentence response."
)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def handle_order(state: AgentState) -> dict:
    chain = order_prompt | llm
    return {
        "response": chain.invoke(
            {"orders": json.dumps(ORDERS_DB), "query": state["customer_query"]}
        ).content
    }


def handle_returns(state: AgentState) -> dict:
    chain = returns_prompt | llm
    return {
        "response": chain.invoke(
            {"policy": RETURN_POLICY, "query": state["customer_query"]}
        ).content
    }


def handle_billing(state: AgentState) -> dict:
    chain = billing_prompt | llm
    return {
        "response": chain.invoke(
            {"policy": BILLING_POLICY, "query": state["customer_query"]}
        ).content
    }


def handle_product(state: AgentState) -> dict:
    chain = product_prompt | llm
    return {
        "response": chain.invoke(
            {"orders": json.dumps(ORDERS_DB), "query": state["customer_query"]}
        ).content
    }


# ---------------------------------------------------------------------------
# Router edge
# ---------------------------------------------------------------------------

def route_by_category(state: AgentState) -> str:
    return {
        "order_status": "handle_order",
        "returns": "handle_returns",
        "billing": "handle_billing",
        "product_info": "handle_product",
    }[state["category"]]


# ---------------------------------------------------------------------------
# Graph factory
# ---------------------------------------------------------------------------

def build_agent() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("classify_query", classify_query)
    graph.add_node("handle_order", handle_order)
    graph.add_node("handle_returns", handle_returns)
    graph.add_node("handle_billing", handle_billing)
    graph.add_node("handle_product", handle_product)

    graph.set_entry_point("classify_query")
    graph.add_conditional_edges(
        "classify_query",
        route_by_category,
        ["handle_order", "handle_returns", "handle_billing", "handle_product"],
    )
    for handler in ["handle_order", "handle_returns", "handle_billing", "handle_product"]:
        graph.add_edge(handler, END)

    return graph.compile()
