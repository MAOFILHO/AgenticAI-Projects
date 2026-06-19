"""Pattern 1: FAISS vector store + similarity search + LCEL RAG chain.

This is the baseline RAG pattern: embed the corpus into FAISS, retrieve the
top-K most similar chunks by cosine/L2 distance, and answer with an LCEL
chain (retriever | format_docs -> prompt -> llm).
"""
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from src import config
from src.patterns.base import RagPattern, RetrievedChunk

RAG_PROMPT = ChatPromptTemplate.from_template(
    """You are an expert assistant. Answer the question using ONLY the provided context.
If the answer is not in the context, say "I don't know." Keep the answer detailed.

Question: {question}
Context: {context}
Answer:"""
)


def _format_docs(docs):
    return "\n\n".join(d.page_content for d in docs)


class FaissSimilarityPattern(RagPattern):
    name = "FAISS Similarity Search"
    description = "FAISS vector store, top-K similarity search, LCEL RAG chain."

    def __init__(self, search_type="similarity", search_kwargs=None):
        self.search_type = search_type
        self.search_kwargs = search_kwargs or {"k": config.TOP_K}
        self.embeddings = OpenAIEmbeddings(model=config.EMBEDDING_MODEL)
        self.llm = ChatOpenAI(model=config.GENERATOR_LLM, temperature=config.GENERATOR_TEMPERATURE)
        self.vectorstore = None
        self.retriever = None

    def build(self, corpus):
        self.vectorstore = FAISS.from_documents(documents=corpus, embedding=self.embeddings)
        self.retriever = self.vectorstore.as_retriever(
            search_type=self.search_type, search_kwargs=self.search_kwargs
        )

    def retrieve(self, question: str):
        docs = self.retriever.invoke(question, config=config.runnable_config())
        return [RetrievedChunk(page_content=d.page_content, metadata=d.metadata) for d in docs]

    def generate(self, question: str, retrieved=None):
        if retrieved is None:
            retrieved = self.retrieve(question)
        context = "\n\n".join(d.page_content for d in retrieved)
        chain = RAG_PROMPT | self.llm
        result = chain.invoke({"question": question, "context": context}, config=config.runnable_config())
        return result.content
