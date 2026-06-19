#!/usr/bin/env python3
"""Compatibility shim for ragas + langchain-community 0.4.x.

ragas (0.3.x/0.4.x) unconditionally does
`from langchain_community.chat_models.vertexai import ChatVertexAI` at import
time, but `langchain_community.chat_models.vertexai` was removed in
langchain-community 0.4.x (moved to the separate `langchain-google-vertexai`
package). This breaks `import ragas` entirely, even for OpenAI-only usage.

This script writes a minimal stub module at
`<site-packages>/langchain_community/chat_models/vertexai.py` so the import
succeeds. The stub's `ChatVertexAI` class is never actually used by this
project (all LLM calls go through OpenAI).

Run automatically by `install.sh`. Safe to re-run (idempotent) -- e.g. after
`pip install --upgrade langchain-community` removes the file again.
"""
import importlib
import os

STUB_CONTENT = '''"""Compatibility shim -- see scripts/patch_ragas_vertexai_shim.py."""


class ChatVertexAI:  # pragma: no cover - import-time shim only
    def __init__(self, *args, **kwargs):
        raise ImportError(
            "ChatVertexAI is not available: this is a compatibility shim for "
            "ragas' import of langchain_community.chat_models.vertexai, which "
            "was removed from langchain-community 0.4.x. Install "
            "langchain-google-vertexai if you actually need Vertex AI."
        )
'''


def main():
    try:
        chat_models = importlib.import_module("langchain_community.chat_models")
    except ImportError:
        print("langchain_community not installed; skipping ragas compatibility shim.")
        return

    target_dir = os.path.dirname(chat_models.__file__)
    target_path = os.path.join(target_dir, "vertexai.py")

    if os.path.exists(target_path):
        print(f"Shim already present: {target_path}")
        return

    with open(target_path, "w") as f:
        f.write(STUB_CONTENT)
    print(f"Installed ragas compatibility shim: {target_path}")


if __name__ == "__main__":
    main()
