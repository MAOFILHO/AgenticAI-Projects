"""Pattern 5: Agentic (ReAct) RAG with an iterative retriever tool.

An LLM agent that decides, step by step, when and how to call a
`search_documents` retrieval tool, scoped to the shared paper corpus so it
can be benchmarked head-to-head with the other patterns.

The agent can call the retrieval tool more than once (e.g. to reformulate
the query if the first search doesn't look useful), which is the key
difference vs. the single-shot retrieval patterns.
"""
from langchain.agents import create_agent
from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from src import config
from src.patterns.base import RagPattern, RetrievedChunk

SYSTEM_PROMPT = """You are a research assistant answering questions about a corpus of \
machine learning papers and Wikipedia articles.

Use the `search_documents` tool to find relevant passages before answering. \
If the first search results don't seem to answer the question, try again with a \
reformulated query. Answer ONLY using information returned by the tool. If you \
still cannot find the answer after searching, say "I don't know."."""


class AgenticRagPattern(RagPattern):
    name = "Agentic RAG (ReAct + Iterative Retrieval)"
    description = "ReAct agent that calls a retrieval tool iteratively, reformulating queries as needed."

    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model=config.EMBEDDING_MODEL)
        self.llm = ChatOpenAI(model=config.GENERATOR_LLM, temperature=config.GENERATOR_TEMPERATURE)
        self.vectorstore = None
        self.retriever = None
        self.agent = None
        self._last_retrieved_docs = []

    def build(self, corpus):
        self.vectorstore = FAISS.from_documents(documents=corpus, embedding=self.embeddings)
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": config.TOP_K})

        retriever = self.retriever
        last_retrieved = self._last_retrieved_docs

        @tool
        def search_documents(query: str) -> str:
            """Search the document corpus (ML papers + Wikipedia) for passages relevant to `query`."""
            docs = retriever.invoke(query)
            last_retrieved.extend(docs)
            return "\n\n".join(
                f"[Source: {d.metadata.get('title', d.metadata.get('source', 'unknown'))}]\n{d.page_content}"
                for d in docs
            )

        self.agent = create_agent(model=self.llm, tools=[search_documents], system_prompt=SYSTEM_PROMPT)

    def _unique_retrieved(self):
        seen = set()
        unique = []
        for d in self._last_retrieved_docs:
            key = d.page_content
            if key not in seen:
                seen.add(key)
                unique.append(RetrievedChunk(page_content=d.page_content, metadata=d.metadata))
        return unique[: config.TOP_K]

    def retrieve(self, question: str):
        """Run the agent and return the union of all chunks it retrieved while answering."""
        _, _ = self.run(question)
        return self._unique_retrieved()

    def generate(self, question: str, retrieved=None):
        # `retrieved` is ignored: the agent performs its own (possibly iterative) retrieval.
        _, answer = self.run(question)
        return answer

    def run(self, question: str):
        self._last_retrieved_docs.clear()
        result = self.agent.invoke(
            {"messages": [{"role": "user", "content": question}]}, config=config.runnable_config()
        )
        final_msg = result["messages"][-1]
        answer = final_msg.content if hasattr(final_msg, "content") else str(final_msg)
        return self._unique_retrieved(), answer
