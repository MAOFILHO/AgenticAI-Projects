"""Pattern 3: ChromaDB vector store + similarity search + LCEL RAG chain.

ChromaDB is a persistent vector database (vs. FAISS's pure in-memory index).
Each run uses a fresh, uniquely-named
collection in a temp directory so repeated evaluation runs don't collide.
"""
import shutil
import tempfile

from langchain_chroma import Chroma
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


class ChromaSimilarityPattern(RagPattern):
    name = "ChromaDB Similarity Search"
    description = "ChromaDB persistent vector store, top-K similarity search, LCEL RAG chain."

    def __init__(self, search_type="similarity", search_kwargs=None, collection_name="rag_eval_collection"):
        self.search_type = search_type
        self.search_kwargs = search_kwargs or {"k": config.TOP_K}
        self.collection_name = collection_name
        self.embeddings = OpenAIEmbeddings(model=config.EMBEDDING_MODEL)
        self.llm = ChatOpenAI(model=config.GENERATOR_LLM, temperature=config.GENERATOR_TEMPERATURE)
        self.vectorstore = None
        self.retriever = None
        self._persist_dir = None

    def build(self, corpus):
        self._persist_dir = tempfile.mkdtemp(prefix="chroma_")
        self.vectorstore = Chroma.from_documents(
            documents=corpus,
            embedding=self.embeddings,
            collection_name=self.collection_name,
            collection_metadata={"hnsw:space": "cosine"},
            persist_directory=self._persist_dir,
        )
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

    def cleanup(self):
        if self._persist_dir:
            shutil.rmtree(self._persist_dir, ignore_errors=True)
            self._persist_dir = None
