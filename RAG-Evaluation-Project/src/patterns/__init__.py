"""RAG pattern implementations under evaluation."""
from src.patterns.agentic_rag import AgenticRagPattern
from src.patterns.chroma_mmr import ChromaMmrPattern
from src.patterns.chroma_similarity import ChromaSimilarityPattern
from src.patterns.faiss_mmr import FaissMmrPattern
from src.patterns.faiss_similarity import FaissSimilarityPattern
from src.patterns.openai_file_search import OpenAIFileSearchPattern


def get_all_patterns():
    """Return a fresh instance of every RAG pattern, in display/run order."""
    return [
        FaissSimilarityPattern(),
        FaissMmrPattern(),
        ChromaSimilarityPattern(),
        ChromaMmrPattern(),
        AgenticRagPattern(),
        OpenAIFileSearchPattern(),
    ]


__all__ = [
    "get_all_patterns",
    "FaissSimilarityPattern",
    "FaissMmrPattern",
    "ChromaSimilarityPattern",
    "ChromaMmrPattern",
    "AgenticRagPattern",
    "OpenAIFileSearchPattern",
]
