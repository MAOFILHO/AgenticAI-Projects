"""LLM, embeddings, and environment configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


def load_env():
    project_root = Path(__file__).resolve().parent.parent.parent
    load_dotenv(project_root / ".env")


def build_primary_llm() -> ChatOpenAI:
    return ChatOpenAI(model="gpt-5-mini")


def build_secondary_llm() -> ChatOpenAI:
    return ChatOpenAI(model="gpt-4.1-mini", temperature=0.3)


def build_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model="text-embedding-3-small")


def get_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data"


def get_output_dir() -> Path:
    """Where generated reports/charts (protocol_benchmark_report.json, *.png) are
    written — keeps the project root free of run artifacts. Created on first use.
    """
    output_dir = Path(__file__).resolve().parent.parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir


# --- Protocol benchmark config ---

def get_fault_mode(protocol: str) -> str:
    """Fault mode for a protocol: none | timeout | error | malformed | refused."""
    return os.getenv(f"FAULT_MODE_{protocol.upper()}", "none").lower()


def get_timeout_s(protocol: str) -> float:
    return float(os.getenv(f"{protocol.upper()}_TIMEOUT_S", "5"))


def get_max_retries(protocol: str) -> int:
    return int(os.getenv(f"{protocol.upper()}_MAX_RETRIES", "2"))


def get_rest_base_url() -> str:
    return os.getenv("REST_BASE_URL", "http://127.0.0.1:8001")


def get_graphql_url() -> str:
    return os.getenv("GRAPHQL_URL", "http://127.0.0.1:8002/graphql")


def get_grpc_pricing_addr() -> str:
    return os.getenv("GRPC_PRICING_ADDR", "127.0.0.1:8003")


def get_webhook_url() -> str:
    return os.getenv("WEBHOOK_URL", "http://127.0.0.1:8004/webhook/shipping-update")


def get_ws_tracking_url() -> str:
    return os.getenv("WS_TRACKING_URL", "ws://127.0.0.1:8005/ws/tracking")


def get_mqtt_broker_host() -> str:
    return os.getenv("MQTT_BROKER_HOST", "127.0.0.1")


def get_mqtt_broker_port() -> int:
    return int(os.getenv("MQTT_BROKER_PORT", "1883"))


def get_amqp_url() -> str:
    return os.getenv("AMQP_URL", "amqp://guest:guest@127.0.0.1:5672/")


def get_soap_url() -> str:
    return os.getenv("SOAP_URL", "http://127.0.0.1:8006/soap")
