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
