"""Pattern 2: FAISS vector store + Maximal Marginal Relevance (MMR) retrieval.

MMR balances relevance with diversity, fetching `MMR_FETCH_K` candidates and
selecting `TOP_K` of them to reduce redundant/near-duplicate chunks compared
to plain similarity search.
"""
from src import config
from src.patterns.faiss_similarity import FaissSimilarityPattern


class FaissMmrPattern(FaissSimilarityPattern):
    name = "FAISS MMR (Diversity)"
    description = "FAISS vector store, Maximal Marginal Relevance retrieval for diverse context."

    def __init__(self):
        super().__init__(
            search_type="mmr",
            search_kwargs={
                "k": config.TOP_K,
                "fetch_k": config.MMR_FETCH_K,
                "lambda_mult": config.MMR_LAMBDA,
            },
        )
