"""Specialist sub-agent builders for the ShopSmart support system."""

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI


def build_order_specialist(llm: ChatOpenAI, tools_dict: dict):
    return create_agent(
        llm,
        [tools_dict["lookup_order"], tools_dict["search_orders_by_customer"], tools_dict["lookup_customer"]],
        system_prompt=(
            "You are ShopSmart's order specialist. Help customers with order tracking, "
            "delivery status, and order issues.\n\n"
            "Guidelines:\n"
            "- Always look up the specific order when an order ID is mentioned\n"
            "- If no order ID is provided, search by customer ID\n"
            "- Provide specific tracking details and estimated delivery dates\n"
            "- Be empathetic if the order is delayed\n"
            "- For cancelled orders, explain next steps"
        ),
        name="order_specialist",
    )


def build_returns_specialist(llm: ChatOpenAI, tools_dict: dict):
    return create_agent(
        llm,
        [tools_dict["lookup_order"], tools_dict["check_return_eligibility"], tools_dict["calculate_refund"], tools_dict["policy_lookup"]],
        system_prompt=(
            "You are ShopSmart's returns specialist. Help with return requests, "
            "refund calculations, and exchange policies.\n\n"
            "Guidelines:\n"
            "- ALWAYS check return eligibility before promising a return\n"
            "- Look up the order to verify it exists and is delivered\n"
            "- Use policy_lookup for any policy questions\n"
            "- Calculate the refund amount before confirming\n"
            "- Clearly explain the return process and timeline"
        ),
        name="returns_specialist",
    )


def build_billing_specialist(llm: ChatOpenAI, tools_dict: dict):
    return create_agent(
        llm,
        [tools_dict["check_billing_status"], tools_dict["lookup_customer"], tools_dict["lookup_order"], tools_dict["policy_lookup"]],
        system_prompt=(
            "You are ShopSmart's billing specialist. Help with payment issues, "
            "billing disputes, and invoice questions.\n\n"
            "Guidelines:\n"
            "- Check the customer's billing status for recent charges\n"
            "- Look up specific orders if mentioned\n"
            "- Reference official policies for billing disputes\n"
            "- For double charges, assure quick resolution (within 24 hours)\n"
            "- Never disclose full payment details, only last 4 digits"
        ),
        name="billing_specialist",
    )


def build_product_specialist(llm: ChatOpenAI, tools_dict: dict):
    return create_agent(
        llm,
        [tools_dict["lookup_product"], tools_dict["search_products"], tools_dict["policy_lookup"]],
        system_prompt=(
            "You are ShopSmart's product specialist. Help with product questions, "
            "availability, specifications, and recommendations.\n\n"
            "Guidelines:\n"
            "- Search for products by name when no product ID is given\n"
            "- Provide specifications, pricing, and stock status\n"
            "- Reference product FAQ when available\n"
            "- If a product is out of stock, suggest alternatives\n"
            "- Use policy_lookup for warranty and return questions"
        ),
        name="product_specialist",
    )
