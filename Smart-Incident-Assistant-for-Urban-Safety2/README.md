# Contoso Smart Incident Assistant for Urban Safety

### Fully Automated Multimodal RAG on Azure

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4o-0078D4?style=flat&logo=microsoft-azure&logoColor=white)](https://azure.microsoft.com/products/ai-services/openai-service)
[![Azure AI Search](https://img.shields.io/badge/Azure%20AI%20Search-Vector%20+%20Hybrid-0078D4?style=flat&logo=microsoft-azure&logoColor=white)](https://azure.microsoft.com/products/ai-services/ai-search)
[![Streamlit](https://img.shields.io/badge/Streamlit-Chat%20UI-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Designed and deployed a production-grade AI Smart Incident Assistant to enhance the analysis of urban safety incidents. The system is built on **Retrieval-Augmented Generation (RAG)** using Microsoft Fabric, which ensures accurate, context-driven answers, and Azure AI technologies, including Azure AI Search, Azure AI Vision, Azure Document Intelligence, and Azure AI Foundry to power the assistant’s capabilities. The project involves processing both structured data (PDFs) and unstructured data (incident images), and using Azure OpenAI for text generation, image captioning, and question-answering tasks, with a Contoso-branded Streamlit web interface and observability via Azure Monitor.

**Key differentiator:** The project is fully automated with Zero Azure Portal visits required. One command provisions all cloud resources, another runs the full data pipeline, and a third launches the web app.

---

## Business Scenario

A **municipal development team** needs an AI-powered assistant to enhance the analysis of urban safety incidents. The assistant integrates three categories of data:

| Data Type | Source | Count |
|---|---|---|
| **Structured** | Incident report PDFs | 50 reports |
| **Visual** | Incident images (floods, fires, collapses, traffic) | 130 images |
| **Procedural** | Standard Operating Procedures | 6 SOPs |

Using **Retrieval-Augmented Generation (RAG)**, the assistant delivers accurate, context-grounded answers with source attribution, inline image display, and multi-turn conversation memory.

---

## Architecture

```
                        AZURE PROVISIONING (automated)
                        python -m src.provision
  ┌──────────────────────────────────────────────────────────────┐
  │  Resource Group ─► OpenAI (GPT-4o + Embeddings)              │
  │                 ─► Document Intelligence (F0)                │
  │                 ─► AI Vision (S1)                            │
  │                 ─► AI Search (Free)                          │
  │                 ─► Application Insights (telemetry)          │
  │                 ─► .env auto-generated                       │
  └──────────────────────────────────────────────────────────────┘
                                │
                                ▼
                      DATA PIPELINE (automated)
                      python -m src.pipeline
  ┌──────────────────────────────────────────────────────────────┐
  │                                                              │
  │  50 PDFs ──► Azure Doc Intelligence ──► parsed_incidents.json│
  │  130 Images ► GPT-4o Vision Captioning ► parsed_images.json  │
  │  6 SOPs ──► Text Parsing ─────────────► parsed_sops.json     │
  │                        │                                     │
  │                        ▼                                     │
  │              text-embedding-3-small (1536-dim)               │
  │                        │                                     │
  │                        ▼                                     │
  │              Azure AI Search (HNSW Vector Index)             │
  │              186 documents indexed                           │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘
                                │
                                ▼
                      STREAMLIT WEB APP (Contoso UI)
                      streamlit run src/web/app.py
  ┌──────────────────────────────────────────────────────────────┐
  │                                                              │
  │  User Query ─► Embed ─► Hybrid Search ─► Top-k Docs ─► GPT   |
  │                                                              |
  │                                    Context-aware Response    │
  │                                                              │
  │  + Chat history memory (10-turn rolling window)              │
  │  + Source attribution with inline image display              │
  │  + Optional SerpAPI web search augmentation                  │
  │  + Azure Monitor OpenTelemetry tracing                       │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘
```

---

## Azure Services

| Service | Purpose | SKU |
|---|---|---|
| **Azure OpenAI — GPT-4o** | Image captioning + RAG answer generation | S0 (pay-per-use) |
| **Azure OpenAI — Embeddings** | Text to 1536-dim semantic vectors | S0 (pay-per-use) |
| **Azure Document Intelligence** | Extract text from incident report PDFs | F0 (free) |
| **Azure AI Vision** | Image processing capabilities | S1 |
| **Azure AI Search** | Hybrid vector + keyword search index | Free |
| **Application Insights** | Observability, tracing, metrics | Free (5 GB/month) |

**Estimated cost:** ~$2–6/month for demo usage.

---

## Quick Start

### Prerequisites

- **Python 3.10 or higher** (tested with 3.12; requires 3.10+ for `str | None` type union syntax)
- [Azure CLI 2.50+](https://aka.ms/installazurecli) installed and logged in (`az login`)
- An active Azure subscription
- **macOS only:** Xcode Command Line Tools (`xcode-select --install`)

### 1. Clone and Install

```bash
git clone https://github.com/MAOFILHO/AgenticAI-Projects/tree/main/Smart-Incident-Assistant-for-Urban-Safety2
cd Smart-Incident-Assistant-for-Urban-Safety2
python3.12 -m venv .venv        # Requires Python 3.10+
source .venv/bin/activate        # macOS/Linux
make install                     # Installs all dependencies + upgrades pip
```
> **Note:** If `python3.12` is not available, use any Python 3.10+ interpreter to create the venv.

<img width="923" height="912" alt="Screenshot 2026-06-18 at 5 45 24 PM" src="https://github.com/user-attachments/assets/d5e7223b-b4dd-4a8d-9ac2-a219c0d000b6" />


### 2. Provision Azure Resources

```bash
make provision
```
Creates all Azure resources automatically and generates your `.env` file with real keys and endpoints. No portal visits needed.

<img width="925" height="909" alt="Screenshot 2026-06-18 at 5 45 50 PM" src="https://github.com/user-attachments/assets/08c7694e-a80c-45ec-a3b8-9d193f7bd7e2" />


### 3. Validate Environment

```bash
make smoke-test
```
Runs 29 checks: Python version, packages, Azure CLI, `.env` config, data directories, API connectivity.

<img width="924" height="772" alt="Screenshot 2026-06-18 at 5 46 48 PM" src="https://github.com/user-attachments/assets/e394b2e1-1c4e-474d-9deb-284b4e6967c4" />


### 4. Run the Data Pipeline

```bash
make pipeline
```
Extracts text from 50 PDFs, captions 130 images with GPT-4o Vision, parses 6 SOPs, generates embeddings, and uploads 186 documents to Azure AI Search. Takes ~15 minutes (image captioning is the bottleneck).

<img width="926" height="909" alt="Screenshot 2026-06-18 at 5 47 09 PM" src="https://github.com/user-attachments/assets/3189e156-aef3-4d92-9d95-8f1c3f6950d7" />
<img width="919" height="904" alt="Screenshot 2026-06-18 at 5 47 42 PM" src="https://github.com/user-attachments/assets/fae80fd9-9318-4c41-8e16-1e3f4b474a25" />


### 5. Launch the Web App

```bash
make run
```
<img width="924" height="208" alt="Screenshot 2026-06-18 at 5 48 21 PM" src="https://github.com/user-attachments/assets/d214157f-48e6-48b6-8850-9c88733d5cd6" />

Open `http://localhost:8501` and log in with:

| Field | Value |
|---|---|
| **Username** | `testuser` |
| **Password** | `MyPassword123!` |

Credentials are configurable via `APP_USERNAME` and `APP_PASSWORD` in `.env`.

<img width="1270" height="931" alt="Screenshot 2026-06-18 at 8 29 50 AM" src="https://github.com/user-attachments/assets/497cf683-6935-4d21-a3d3-ee7eed6903a1" />

---

## Sample Queries

Try these in the web app:

- "What fire incidents were reported in Zone A?"
- "What incidents occurred in Zone B?"
- "Which SOP is used for fire response?"
- "List pothole incidents and their actions taken"
- "Show me all flooding incidents with photos"
- "What actions were taken for severe incidents in Zone C?"
- "What is the protocol for electrical hazards?"
- "Give me reports involving both fire and flooding"

**Multi-turn follow-ups** (the assistant remembers context):
- "How severe were those incidents?"
- "What images do we have related to that?"
- "Summarize everything we've discussed so far"

---

## Features

### Multimodal RAG
Incident images are captioned by GPT-4o Vision and indexed alongside text documents, enabling image content to be retrieved and displayed via text queries.

### Hybrid Search
Combines keyword-based BM25 matching with vector cosine similarity (HNSW, 1536-dim embeddings) for best-of-both retrieval accuracy.

### Chat History Memory
Rolling 10-turn window maintains conversational context for follow-up questions, cross-topic references, and summary requests.

### Source Attribution
Every response includes expandable source cards showing document type, filename, and content snippet. Image-type sources display the actual photo inline.

### Secure Login
Username/password authentication with configurable credentials via `.env` Session tracking with unique session IDs.

### Multi-Page Web App
- **Chat** — RAG chat interface with source attribution and inline images
- **Profile** — User account details, session info, login duration
- **Settings** — Model config, Azure resource endpoints, pipeline status, session telemetry

### Web Search (Optional)
Supplements RAG answers with live web search results via SerpAPI. Toggle in the sidebar. Requires a SerpAPI key in `.env`.

### Observability & Telemetry
Uses **Azure Monitor OpenTelemetry** for production-grade observability:
- Per-query tracing with retrieval/generation latency spans
- Custom metrics: query counters, latency histograms, error rates
- Application Insights **Agents view** for agentic workload traces
- Session telemetry dashboard in the Settings page
- Free tier: 5 GB/month ingestion, 90-day metric retention

### Cleanup & Verification
- `python -m src.provision --cleanup` lists resources, deletes the resource group, and confirms
- `python -m src.provision --verify-cleanup` checks for orphaned resources and confirms everything is gone

---

## Project Structure

```
Smart-Incident-Assistant-for-Urban-Safety2/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── .env.template                      # Environment variable template
├── .gitignore                         # Git ignore rules
├── Makefile                           # Convenience targets
│
├── pdfs/                              # 50 incident report PDFs (input)
├── images/                            # 130 incident images (input)
├── sops/                              # 6 SOP text files (input)
├── data/                              # Generated JSON outputs (gitignored)
│
└── src/
    ├── config.py                      # Centralized configuration from .env
    ├── provision.py                   # Azure CLI resource provisioning
    ├── pipeline.py                    # End-to-end pipeline orchestrator
    ├── smoke_test.py                  # Production readiness checks (29 tests)
    ├── telemetry.py                   # Azure Monitor OpenTelemetry
    │
    ├── extraction/                    # Data extraction modules
    │   ├── extract_incidents.py       # PDF → JSON (Azure Document Intelligence)
    │   ├── extract_images.py          # Image → caption (GPT-4o Vision)
    │   └── extract_sops.py           # SOP .txt → JSON
    │
    ├── indexing/                       # Search index modules
    │   ├── create_index.py            # Create HNSW vector index
    │   └── upload_documents.py        # Embed + batch upload to Azure AI Search
    │
    ├── search/                        # Search modules
    │   ├── hybrid_search.py           # Hybrid vector + keyword search
    │   └── web_search.py              # SerpAPI web search (optional)
    │
    ├── rag/
    │   └── engine.py                  # RAGEngine class (retrieve + generate + history)
    │
    └── web/
        ├── app.py                     # Login gate + page router
        ├── views/
        │   ├── chat.py                # RAG chat interface
        │   ├── profile.py             # User profile page
        │   └── settings.py            # Settings + telemetry dashboard
        └── assets/
            └── contoso_logo.svg       # Contoso branding
```

---

## Makefile Targets

```bash
make install          # Install Python dependencies
make provision        # Provision Azure resources + generate .env
make smoke-test       # Run full smoke test (29 checks incl. API connectivity)
make smoke-test-quick # Quick smoke test (skip API calls)
make extract          # Extract data only (PDFs, images, SOPs)
make index            # Create index + upload embeddings only
make pipeline         # Full pipeline (extract + index)
make pipeline-force   # Pipeline with forced re-extraction
make run              # Start Streamlit web app
make clean-azure      # Delete all Azure resources (destructive)
make verify-cleanup   # Verify all Azure resources are deleted
make clean-data       # Remove generated data/
```

---

## Web Search (Optional)

The assistant can supplement RAG answers with live web search results via SerpAPI:

1. Get an API key from [serpapi.com](https://serpapi.com)
2. Add `SERP_API_KEY=your_key` to `.env`
3. Toggle "Enable Web Search" in the Streamlit sidebar

---

## Smoke Test

Run the production readiness smoke test at any time to validate your environment:

```bash
python -m src.smoke_test           # Full check (29 tests incl. Azure API connectivity)
python -m src.smoke_test --quick   # Quick check (skip API calls)
# or
make smoke-test
make smoke-test-quick
```

The smoke test validates: Python version, all packages, Azure CLI login, `.env` configuration, input data directories, parsed data files, Azure OpenAI API connectivity, Azure AI Search index status, and Document Intelligence connectivity.

---

## Cleanup

Delete all Azure resources when done to stop billing:

```bash
# Step 1: Delete all resources (lists them first, then deletes)
python -m src.provision --cleanup
# or
make clean-azure

# Step 2: Verify everything is gone (checks for orphaned resources)
python -m src.provision --verify-cleanup
# or
make verify-cleanup
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **LLM** | Azure OpenAI GPT-4o (generation + vision) |
| **Embeddings** | Azure OpenAI text-embedding-3-small (1536-dim) |
| **Search** | Azure AI Search (HNSW + BM25 hybrid) |
| **PDF Extraction** | Azure Document Intelligence |
| **Frontend** | Streamlit with custom Contoso CSS |
| **Observability** | Azure Monitor OpenTelemetry + Application Insights |
| **Web Search** | SerpAPI + GPT-4o analysis (optional) |
| **Provisioning** | Azure CLI via Python subprocess |
| **Language** | Python 3.10+ |

---

## Author

**Marcos Oliveira** — [LinkedIn](https://www.linkedin.com/in/mfilho1/) | [GitHub](https://github.com/MAOFILHO)

Built with Azure AI services and Claude Code.
