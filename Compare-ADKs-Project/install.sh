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
echo "=== Phase 3: lock opentelemetry to the version google-adk requires ==="
pip install \
    "opentelemetry-api==1.41.0" \
    "opentelemetry-sdk==1.41.0" \
    "opentelemetry-semantic-conventions==0.62b0" \
    --upgrade --quiet

echo ""
echo "=== Verifying all imports ==="
python -c "
import crewai;                               print('  crewai         OK')
import agents;                               print('  openai-agents  OK')
from autogen_agentchat.agents import AssistantAgent; print('  autogen        OK')
from google.adk.agents import LlmAgent;     print('  google-adk     OK')
from langgraph.graph import StateGraph;      print('  langgraph      OK')
print()
print('Note: pip will show dependency-conflict WARNINGS above — these are')
print('expected and do not affect runtime. Both crewai and google-adk import OK.')
"

echo ""
echo "All dependencies installed."
echo "Next: cp .env.example .env  ->  add OPENAI_API_KEY  ->  python main.py"
