"""Load the evaluation dataset and build the document corpus used by all RAG patterns."""
import json
from glob import glob

from langchain_community.document_loaders import JSONLoader, PyMuPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src import config


def load_eval_dataset():
    """Load the 40-question evaluation dataset (question, ground_truth, gold_context, source_document)."""
    with open(config.EVAL_DATASET_PATH, "r") as f:
        return json.load(f)


def _load_wiki_docs():
    """Load Wikipedia articles from the JSONL corpus into LangChain Documents."""
    jsonl_path = f"{config.DOCS_DIR}/wikidata_rag_demo.jsonl"
    loader = JSONLoader(file_path=jsonl_path, jq_schema=".", text_content=False, json_lines=True)
    raw_docs = loader.load()

    wiki_docs = []
    for doc in raw_docs:
        data = json.loads(doc.page_content)
        content = " ".join(data["paragraphs"])
        wiki_docs.append(
            Document(
                page_content=content,
                metadata={"title": data["title"], "id": data["id"], "source": "Wikipedia"},
            )
        )
    return wiki_docs


def _load_pdf_chunks(chunk_size=None, chunk_overlap=None):
    """Load and chunk all PDFs in the corpus directory."""
    chunk_size = chunk_size or config.CHUNK_SIZE
    chunk_overlap = chunk_overlap or config.CHUNK_OVERLAP

    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    pdf_files = sorted(glob(f"{config.DOCS_DIR}/*.pdf"))

    paper_docs = []
    for fp in pdf_files:
        pages = PyMuPDFLoader(fp).load()
        paper_docs.extend(splitter.split_documents(pages))
    return paper_docs


def load_corpus(chunk_size=None, chunk_overlap=None, include_wiki=False):
    """Build the document corpus used by every RAG pattern.

    The 40-question eval dataset's gold_context comes exclusively from the 4 PDF
    papers, so the corpus defaults to PDF chunks only. This keeps embedding cost/time
    manageable since the corpus is re-embedded once per pattern (6 patterns).

    Set include_wiki=True to also index the ~1,800 Wikipedia articles from
    rag_docs/wikidata_rag_demo.jsonl -- useful for testing retrieval precision
    against a larger, noisier corpus, but
    significantly increases embedding time/cost for every pattern.
    """
    paper_docs = _load_pdf_chunks(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    if not include_wiki:
        return paper_docs

    wiki_docs = _load_wiki_docs()
    return wiki_docs + paper_docs
