"""
config.py — Model instances and environment setup.
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

load_dotenv()

if not os.environ.get("OPENAI_API_KEY"):
    raise EnvironmentError(
        "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
    )

# Primary model: gpt-4o-mini as a reasoning-capable replacement for gpt-5-mini
# Change to "gpt-5-mini" once it is available in your org.
PRIMARY_MODEL = os.environ.get("PRIMARY_MODEL", "gpt-4o-mini")
SECONDARY_MODEL = os.environ.get("SECONDARY_MODEL", "gpt-4o-mini")

llm_primary = ChatOpenAI(model=PRIMARY_MODEL)
llm_secondary = ChatOpenAI(model=SECONDARY_MODEL, temperature=0.3)
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
