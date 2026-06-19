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

# Primary model: gpt-5-mini (reasoning model — NO temperature parameter)
llm_primary = ChatOpenAI(model="gpt-5-mini")

# Secondary model: gpt-4.1-mini (supports temperature for response generation)
llm_secondary = ChatOpenAI(model="gpt-4.1-mini", temperature=0.3)

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

print("LLM instances initialized:")
print(f"  Primary:   gpt-5-mini (reasoning model, no temperature)")
print(f"  Secondary: gpt-4.1-mini (temperature=0.3, for response generation)")
