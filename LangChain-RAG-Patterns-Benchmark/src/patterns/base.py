"""Common interface implemented by every RAG pattern.

Each pattern wraps a different retrieval/generation strategy extracted from the
source notebooks, but exposes the same two operations so the evaluation
pipeline (src/evaluator.py) can run all of them identically:

    retrieve(question) -> list[RetrievedChunk]
    generate(question, retrieved) -> str

`RetrievedChunk` is a tiny duck-typed container with `.page_content` and
`.metadata`, mirroring `langchain_core.documents.Document` so the retrieval
metric functions (src/metrics/retrieval_metrics.py) work for every pattern,
including the OpenAI file_search pattern which doesn't use LangChain.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetrievedChunk:
    page_content: str
    metadata: dict = field(default_factory=dict)


class RagPattern:
    """Base class for a single RAG pattern under evaluation."""

    #: Short, human-readable name shown in terminal output and reports.
    name = "base"

    #: One-line description of the retrieval/generation strategy.
    description = ""

    def build(self, corpus):
        """One-time setup: build vector stores / agents / cloud resources.

        `corpus` is the list of LangChain Documents returned by
        src.data_loader.load_corpus(). Implementations that don't need the
        local corpus (e.g. the OpenAI file_search pattern, which uploads its
        own files) may ignore it.
        """
        raise NotImplementedError

    def retrieve(self, question: str) -> list[RetrievedChunk]:
        """Return the top-K retrieved chunks for `question`."""
        raise NotImplementedError

    def generate(self, question: str, retrieved: list[RetrievedChunk] = None) -> str:
        """Return the generated answer for `question`.

        If `retrieved` is None, implementations should perform their own
        retrieval as part of generation (e.g. agentic / hosted patterns).
        """
        raise NotImplementedError

    def run(self, question: str):
        """Convenience: return (retrieved_chunks, answer) for `question`.

        Default implementation retrieves once and reuses the chunks for
        generation. Patterns where retrieval is itself part of generation
        (agentic, hosted file_search) override this to avoid duplicate work.
        """
        retrieved = self.retrieve(question)
        answer = self.generate(question, retrieved=retrieved)
        return retrieved, answer

    def cleanup(self):
        """Release any external resources (cloud vector stores, temp files, ...)."""
        pass

    def __repr__(self):
        return f"<RagPattern {self.name}>"
