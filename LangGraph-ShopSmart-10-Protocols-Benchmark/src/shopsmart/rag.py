"""FAISS RAG knowledge base from policies.md."""

from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings


def build_policy_retriever(policies_text: str, embeddings: OpenAIEmbeddings):
    """
    Build a FAISS retriever from the raw policies markdown text.

    Returns a LangChain retriever (similarity search, top-3 chunks).
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n## ", "\n### ", "\n- ", "\n", " "],
    )
    chunks = splitter.split_text(policies_text)

    docs = [
        Document(
            page_content=chunk,
            metadata={"source": "policies.md", "chunk_index": i},
        )
        for i, chunk in enumerate(chunks)
    ]

    vectorstore = FAISS.from_documents(docs, embeddings)
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3},
    )

    print(f"RAG knowledge base ready: {len(chunks)} policy chunks indexed.")
    return retriever
