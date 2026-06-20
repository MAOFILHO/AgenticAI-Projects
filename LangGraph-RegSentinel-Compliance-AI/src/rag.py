"""RAG: embed the regulation corpus into a Chroma vector store."""
import glob
import os

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from src.config import FFT_REG_DIR, EMBEDDING_MODEL

_vectorstore: Chroma | None = None


def _build_vectorstore() -> Chroma:
    reg_paths = sorted(
        p for p in glob.glob(str(FFT_REG_DIR / "*.md"))
        if not p.endswith("INDEX.md")
    )
    reg_docs = []
    for p in reg_paths:
        text = open(p, encoding="utf-8").read()
        reg_id = os.path.splitext(os.path.basename(p))[0]
        reg_docs.append(
            Document(
                page_content=text,
                metadata={"regulation_id": reg_id, "source": os.path.basename(p)},
            )
        )

    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    vs = Chroma.from_documents(
        documents=reg_docs,
        embedding=embeddings,
        collection_name="fft_regulations",
    )
    print(f"✓ Vector store built: {len(reg_docs)} regulation docs indexed")
    return vs


def get_vectorstore() -> Chroma:
    """Return the singleton vector store, building it on first call."""
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = _build_vectorstore()
    return _vectorstore
