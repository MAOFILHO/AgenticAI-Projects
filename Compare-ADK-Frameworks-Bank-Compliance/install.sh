#!/bin/bash
# Two-phase install to resolve the opentelemetry conflict between
# crewai 1.14.6 (pins opentelemetry~=1.34) and google-adk 2.2.0 (requires >=1.36).
#
# Strategy:
#   1. Install everything except crewai (sets opentelemetry to >=1.36).
#   2. Install crewai with --no-deps to bypass its stale opentelemetry pin.
#   3. Force the full opentelemetry 1.41 stack so google-adk can import cleanly.
#   Both packages work fine at runtime — the conflict is metadata-only.
set -e

echo "=== Phase 1: install all packages except CrewAI ==="
pip install -r requirements-phase1.txt

echo ""
echo "=== Phase 2: install CrewAI without its opentelemetry pin ==="
pip install crewai==1.14.6 --no-deps
pip install crewai-core==1.14.6 --no-deps

echo ""
echo "=== Phase 2b: restore CrewAI's other runtime deps skipped by --no-deps ==="
# --no-deps also skips these (unrelated to the opentelemetry conflict) — without
# them `import crewai` fails on a missing module a few frames deep.
# opentelemetry-exporter-otlp-proto-http is deliberately left out of this
# unpinned batch: leaving it unpinned lets pip resolve it to whatever is
# newest at install time (currently 1.44.x), which expects sdk symbols that
# don't exist in the 1.41.0 sdk Phase 3 pins below and breaks `import crewai`
# with an ImportError several frames deep. It's pinned alongside the rest of
# the opentelemetry stack in Phase 3 instead.
pip install \
    json_repair \
    portalocker \
    rich \
    appdirs \
    chromadb \
    json5 \
    --quiet

echo ""
echo "=== Phase 3: lock opentelemetry to the version google-adk requires ==="
pip install \
    "opentelemetry-api==1.41.0" \
    "opentelemetry-sdk==1.41.0" \
    "opentelemetry-semantic-conventions==0.62b0" \
    "opentelemetry-exporter-otlp-proto-http==1.41.0" \
    --upgrade --quiet

echo ""
echo "=== Verifying all imports ==="
python -c "
import crewai;                               print('  crewai         OK')
import agents;                               print('  openai-agents  OK')
from autogen_agentchat.agents import AssistantAgent; print('  autogen        OK')
from google.adk.agents import LlmAgent;     print('  google-adk     OK')
from langgraph.graph import StateGraph;      print('  langgraph      OK')
from pydantic_ai import Agent;               print('  pydantic-ai    OK')
from pydantic_graph import GraphBuilder;     print('  pydantic-graph OK')
print()
print('Note: pip will show dependency-conflict WARNINGS above — these are')
print('expected and do not affect runtime. Both crewai and google-adk import OK.')
"

echo ""
echo "All dependencies installed."
echo "Next: cp .env.example .env  ->  add OPENAI_API_KEY  ->  python main.py"
