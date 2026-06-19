"""Pattern 4: ChromaDB vector store + Maximal Marginal Relevance (MMR) retrieval.

Same as the FAISS MMR pattern, but backed by ChromaDB. Useful for comparing
how MMR diversity behaves across vector store backends.
"""
from src import config
from src.patterns.chroma_similarity import ChromaSimilarityPattern


class ChromaMmrPattern(ChromaSimilarityPattern):
    name = "ChromaDB MMR (Diversity)"
    description = "ChromaDB vector store, Maximal Marginal Relevance retrieval for diverse context."

    def __init__(self):
        super().__init__(
            search_type="mmr",
            search_kwargs={
                "k": config.TOP_K,
                "fetch_k": config.MMR_FETCH_K,
                "lambda_mult": config.MMR_LAMBDA,
            },
            collection_name="rag_eval_collection_mmr",
        )
