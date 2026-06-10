"""Pattern 6: OpenAI Responses API + hosted Vector Store + file_search tool.

Unlike the other patterns, this one doesn't use LangChain at all -- it uploads the PDF
corpus to an OpenAI-hosted Vector Store and lets the Responses API's
`file_search` tool handle chunking, embedding and retrieval server-side.

Retrieved chunks are reconstructed from the `file_search_call` output item
(returned via `include=["file_search_call.results"]`) so the same retrieval
metrics (Hit Rate, MRR, Precision@K, ...) can be computed for this pattern.
"""
from glob import glob

from src import config
from src.patterns.base import RagPattern, RetrievedChunk


class OpenAIFileSearchPattern(RagPattern):
    name = "OpenAI File Search (Hosted Vector Store)"
    description = "OpenAI Responses API + hosted Vector Store with the file_search tool."

    def __init__(self):
        # Langfuse-wrapped OpenAI client (when LANGFUSE_* keys are set) so this
        # raw-SDK pattern -- the only one LangSmith can't trace -- is still observed.
        OpenAI = config.get_openai_client()
        self.client = OpenAI()
        self.vector_store_id = None
        self.uploaded_file_ids = []

    def build(self, corpus):
        # `corpus` (LangChain Documents) is unused -- this pattern indexes the
        # raw PDF files server-side via OpenAI's hosted Vector Store.
        vector_store = self.client.vector_stores.create(name="rag-eval-comparison")
        self.vector_store_id = vector_store.id

        for pdf_path in sorted(glob(f"{config.DOCS_DIR}/*.pdf")):
            with open(pdf_path, "rb") as f:
                vs_file = self.client.vector_stores.files.upload_and_poll(
                    vector_store_id=self.vector_store_id, file=f
                )
            self.uploaded_file_ids.append(vs_file.id)

    def _call(self, question: str):
        return self.client.responses.create(
            model=config.GENERATOR_LLM,
            input=[{"role": "user", "content": question}],
            tools=[{"type": "file_search", "vector_store_ids": [self.vector_store_id], "max_num_results": config.TOP_K}],
            include=["file_search_call.results"],
        )

    def run(self, question: str):
        response = self._call(question)

        retrieved = []
        for item in response.output:
            if getattr(item, "type", None) == "file_search_call":
                for result in getattr(item, "results", None) or []:
                    retrieved.append(
                        RetrievedChunk(
                            page_content=getattr(result, "text", "") or "",
                            metadata={"source": getattr(result, "filename", "unknown")},
                        )
                    )
        return retrieved, response.output_text

    def retrieve(self, question: str):
        retrieved, _ = self.run(question)
        return retrieved

    def generate(self, question: str, retrieved=None):
        # `retrieved` is ignored: file_search retrieval happens server-side as part of generation.
        _, answer = self.run(question)
        return answer

    def cleanup(self):
        if self.vector_store_id:
            try:
                self.client.vector_stores.delete(self.vector_store_id)
            except Exception:
                pass
        for file_id in self.uploaded_file_ids:
            try:
                self.client.files.delete(file_id)
            except Exception:
                pass
        self.vector_store_id = None
        self.uploaded_file_ids = []
