"""Pattern 7: Multimodal Vision + Text RAG (SecureLife claims agent).

Unlike patterns 1-6, this is not a text-QA pattern evaluated against the
40-question dataset. It is a 3-node LangGraph agent that:
  1. (vision_node) Looks at a vehicle damage photo with gpt-4o and produces a
     structured DamageAssessment.
  2. (policy_node) Runs semantic search (FAISS RAG) over the SecureLife Motor
     Comprehensive policy clauses to find relevant coverage citations.
  3. (synthesize_node) Cross-checks vision + policy + the claim record (loaded
     from SecureLife_claims.db) and produces a structured CoverageDecision,
     including a fraud signal.

`run_demo()` runs the agent over the 3 sample damage photos against the same
claim record and prints a per-scenario decision plus a summary table. It is
invoked separately from `evaluate_pattern()` since its
inputs/outputs (images, coverage decisions) don't fit the text retrieval/
generation metric framework used by patterns 1-6.
"""
import base64
import json
import os
import sqlite3
from typing import List, Optional, TypedDict

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from src import config

PATTERN_NAME = "Multimodal Vision + Text RAG (SecureLife)"
PATTERN_DESCRIPTION = (
    "GPT-4o vision damage assessment + FAISS RAG over policy clauses, "
    "fused by a 3-node LangGraph into a coverage decision."
)

MULTIMODAL_DIR = os.path.join(config.DATA_DIR, "multimodal")
CLAIMS_DB_PATH = os.path.join(MULTIMODAL_DIR, "SecureLife_claims.db")
SAMPLE_IMAGE_FILES = {
    "front_collision": "vehicle-damage.jpg",
    "side_scratch": "side-damage.jpg",
    "total_loss": "backside-damage.png",
}
DEFAULT_CLAIM_ID = "CLM-2025-0001"

MOCK_CLAIM = {
    "claim_id": DEFAULT_CLAIM_ID,
    "full_name": "Anita Rao",
    "city": "Bengaluru",
    "policy_id": "POL-2024-0018",
    "product_name": "SecureLife Motor Comprehensive",
    "policy_type": "Motor Comprehensive",
    "sum_insured": 500000,
    "claim_amount": 435957,
    "diagnosis": "Front-end collision at a traffic light, other driver at fault.",
}

# --- The SecureLife Motor Comprehensive Policy document (10 clauses) ---
POLICY_CLAUSES = {
    "OD-001_OwnDamageCoverage": (
        "Section A — Own Damage Coverage. SecureLife Motor Comprehensive policy covers "
        "loss or damage to the insured vehicle arising from accident, collision, fire, "
        "theft, malicious acts, natural calamities (flood, earthquake, cyclone), and "
        "transit damage. The maximum coverage equals the Insured's Declared Value (IDV) "
        "as stated on the policy schedule, less applicable depreciation and deductibles."
    ),
    "OD-002_TotalLossDefinition": (
        "A vehicle is declared a constructive total loss (CTL) when the cost of repair "
        "exceeds 75% of the IDV at the time of the accident. In CTL cases, the company "
        "settles the IDV in full less the policyholder's compulsory deductible. The "
        "salvage rights transfer to SecureLife unless otherwise agreed."
    ),
    "OD-003_Deductibles": (
        "Compulsory deductibles apply to every own-damage claim: ₹1,000 for vehicles "
        "below 1500cc engine capacity, ₹2,000 for vehicles 1500cc and above. Voluntary "
        "deductible discounts may apply if elected at policy inception. The deductible "
        "is reduced from the assessed repair cost before settlement."
    ),
    "TP-001_ThirdPartyLiability": (
        "Section B — Third-Party Liability. The policy covers the insured's legal "
        "liability for death or bodily injury to a third party and for property damage, "
        "subject to statutory limits set by the Motor Vehicles Act. Third-party "
        "property damage cover is limited to ₹7,50,000 unless extended."
    ),
    "CL-001_ClaimProcedure": (
        "Section C — Claim Procedure. The insured must notify SecureLife within 48 "
        "hours of the incident. Required documents: filled claim form, original police "
        "FIR (for theft, third-party injury, or accident with damages exceeding "
        "₹50,000), driving licence copy, registration certificate (RC), repair estimate "
        "from an authorised garage, post-repair invoice, and photographs of the damage."
    ),
    "CL-002_AuthorisedGarages": (
        "SecureLife operates a cashless repair facility through its network of authorised "
        "garages. The insured may choose cashless settlement (no upfront payment) at any "
        "network garage, or reimbursement settlement at a non-network garage. Cashless "
        "is recommended for claims above ₹50,000 to avoid liquidity gaps."
    ),
    "EX-001_ExclusionsGeneral": (
        "Exclusions: the policy does NOT cover (a) consequential loss, depreciation, "
        "wear and tear, mechanical or electrical breakdown not arising from a covered "
        "peril; (b) damage while the vehicle is used outside its declared geographical "
        "area; (c) damage occurring while the vehicle is driven by a person without a "
        "valid driving licence; (d) damage caused under the influence of alcohol or "
        "drugs; (e) damage from war, mutiny, nuclear perils, or government-ordered seizure."
    ),
    "EX-002_PreexistingDamage": (
        "Pre-existing damage discovered during inspection is excluded from coverage. "
        "SecureLife reserves the right to compare the post-accident photographs against "
        "the pre-policy survey photographs (taken at policy inception). Claims for "
        "damage not consistent with the reported accident description may be denied "
        "and may trigger SIU (Special Investigation Unit) review."
    ),
    "FR-001_FraudIndicators": (
        "Fraud Indicators triggering SIU review: (a) repair estimate exceeds 70% of "
        "IDV without total-loss declaration; (b) claim amount differs from independent "
        "surveyor estimate by more than 30%; (c) photographs inconsistent with the "
        "stated incident description; (d) multiple claims on the same policy within "
        "12 months; (e) policyholder cannot produce a valid police FIR for high-value "
        "claims."
    ),
    "SET-001_SettlementTimeline": (
        "Settlement timeline: SecureLife will acknowledge the claim within 3 working "
        "days, complete inspection within 7 working days, and communicate the settlement "
        "decision within 30 days of receiving all required documents. Settlements via "
        "NEFT to the policyholder's registered bank account."
    ),
}


class DamageAssessment(BaseModel):
    """Structured output from the vision model."""

    damage_type: str = Field(
        description=(
            "Short label: front_collision | rear_collision | side_panel_scratch | "
            "total_loss | minor_dent | windshield_crack | flood_damage | other"
        )
    )
    severity: int = Field(ge=1, le=10, description="1=cosmetic only, 10=total loss / unrepairable")
    estimated_repair_inr: int = Field(description="Indian Rupees repair estimate based on the visible damage")
    parts_affected: List[str] = Field(description="Affected vehicle components")
    confidence: float = Field(ge=0.0, le=1.0, description="Model confidence in its assessment")
    summary: str = Field(description="One-sentence description of what's visible in the photo.")


class CoverageDecision(BaseModel):
    decision: str = Field(description="APPROVE | REVIEW | REJECT")
    confidence: float = Field(ge=0.0, le=1.0)
    estimated_repair_inr: int
    claimed_amount_inr: int
    fraud_signal: bool = Field(
        description=(
            "True if photo damage is inconsistent with claimed amount by >30%, "
            "or if other policy FR-001 indicators apply"
        )
    )
    fraud_signal_reason: str
    coverage_clause_ids: List[str] = Field(description="Policy clauses supporting the coverage decision")
    reasoning: str = Field(description="2-3 sentence explanation")
    next_steps: str = Field(description="What the adjuster should do next")


class AgentState(TypedDict, total=False):
    claim_record: dict
    image_bytes: bytes
    damage_assessment: dict
    policy_citations: List[dict]
    decision: dict


SYNTH_PROMPT = ChatPromptTemplate.from_template(
    "You are SecureLife's claims adjudication assistant. Make a coverage decision "
    "by cross-checking the visual damage assessment against the customer's claim "
    "and the policy clauses.\n\n"
    "Decision rules:\n"
    "  - APPROVE: damage consistent with claim, total covered amount <= sum insured\n"
    "  - REVIEW: any fraud signal triggered, OR ambiguity in damage vs claim\n"
    "  - REJECT: damage type explicitly excluded (see EX-001), or pre-existing damage signs\n\n"
    "Fraud check (per clause FR-001):\n"
    "  - flag if |estimated_repair - claimed_amount| / claimed_amount > 0.30\n"
    "  - flag if estimated_repair > 70% of sum_insured without total-loss declaration\n\n"
    "Claim record:\n{claim_record}\n\n"
    "Vision assessment:\n{damage_assessment}\n\n"
    "Policy clauses retrieved (cite the relevant ones in your decision):\n"
    "{policy_citations}\n"
)


def load_claim(claim_id: str = DEFAULT_CLAIM_ID) -> dict:
    """Load a claim record from SecureLife_claims.db, falling back to a mock claim."""
    if os.path.exists(CLAIMS_DB_PATH):
        conn = sqlite3.connect(CLAIMS_DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT c.*, cu.full_name, cu.city,
                      p.policy_id, p.policy_type, p.sum_insured, p.product_name
               FROM claims c
               JOIN customers cu ON c.customer_id = cu.customer_id
               JOIN policies  p  ON c.policy_id   = p.policy_id
               WHERE c.claim_id = ?""",
            (claim_id,),
        ).fetchall()
        conn.close()
        if rows:
            return dict(rows[0])
    return dict(MOCK_CLAIM)


def load_sample_images() -> dict:
    """Load the 3 sample damage photos as raw bytes, keyed by scenario name."""
    images = {}
    for scenario, filename in SAMPLE_IMAGE_FILES.items():
        with open(os.path.join(MULTIMODAL_DIR, filename), "rb") as f:
            images[scenario] = f.read()
    return images


def build_policy_vectorstore() -> FAISS:
    """Build a FAISS vector store over the SecureLife Motor Comprehensive policy clauses."""
    embeddings = OpenAIEmbeddings(model=config.EMBEDDING_MODEL)
    docs = [Document(page_content=text, metadata={"clause_id": clause_id}) for clause_id, text in POLICY_CLAUSES.items()]
    return FAISS.from_documents(docs, embeddings)


def policy_lookup(vectorstore: FAISS, query: str, k: int = 2) -> list:
    hits = vectorstore.similarity_search(query, k=k)
    return [{"clause_id": h.metadata["clause_id"], "text": h.page_content} for h in hits]


def build_graph(vectorstore: FAISS):
    """Build the 3-node vision -> policy -> synthesize LangGraph."""
    vision_llm = ChatOpenAI(model="gpt-4o", temperature=0)
    vision_chain = vision_llm.with_structured_output(DamageAssessment)

    synthesizer_llm = ChatOpenAI(model=config.GENERATOR_LLM, temperature=0.2)
    synth_chain = synthesizer_llm.with_structured_output(CoverageDecision)

    def analyse_damage_photo(image_bytes: bytes) -> DamageAssessment:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:image/png;base64,{b64}"
        message = {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "You are SecureLife's vehicle damage assessor. Look at this photo "
                        "of a damaged vehicle and produce a structured assessment. "
                        "Be realistic about INR repair cost estimates for the Indian market."
                    ),
                },
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
        return vision_chain.invoke([message], config=config.runnable_config())

    def vision_node(state: AgentState) -> dict:
        result = analyse_damage_photo(state["image_bytes"])
        return {"damage_assessment": result.model_dump()}

    def policy_node(state: AgentState) -> dict:
        damage = state["damage_assessment"]
        queries = [
            f"Is {damage['damage_type']} covered under own damage?",
            "What deductible applies for a motor own-damage claim?",
            "When is a vehicle declared a total loss?",
            "What documents are required for a claim?",
        ]
        seen = set()
        citations = []
        for q in queries:
            for hit in policy_lookup(vectorstore, q, k=2):
                if hit["clause_id"] not in seen:
                    seen.add(hit["clause_id"])
                    citations.append(hit)
        return {"policy_citations": citations}

    def synthesize_node(state: AgentState) -> dict:
        rendered = SYNTH_PROMPT.format_messages(
            claim_record=json.dumps(state["claim_record"], indent=2),
            damage_assessment=json.dumps(state["damage_assessment"], indent=2),
            policy_citations="\n".join(f"- [{c['clause_id']}] {c['text'][:200]}..." for c in state["policy_citations"]),
        )
        decision = synth_chain.invoke(rendered, config=config.runnable_config())
        return {"decision": decision.model_dump()}

    graph = StateGraph(AgentState)
    graph.add_node("vision", vision_node)
    graph.add_node("policy", policy_node)
    graph.add_node("synthesize", synthesize_node)
    graph.set_entry_point("vision")
    graph.add_edge("vision", "policy")
    graph.add_edge("policy", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()


def run_demo(claim_id: str = DEFAULT_CLAIM_ID, verbose: bool = True) -> dict:
    """Run the multimodal claims agent on all 3 sample damage photos.

    Returns a dict with keys: pattern, description, claim_record, scenarios
    (per-scenario damage_assessment + decision), build_time_sec, total_time_sec.
    """
    import time

    if verbose:
        print("\n" + "=" * 70)
        print(f"  Now running the RAG Evaluation pipeline using: {PATTERN_NAME}")
        print(f"  {PATTERN_DESCRIPTION}")
        print("=" * 70)

    t0 = time.time()
    claim_record = load_claim(claim_id)
    vectorstore = build_policy_vectorstore()
    agent = build_graph(vectorstore)
    build_time = time.time() - t0

    if verbose:
        print(f"  Policy vector store + agent built in {build_time:.1f}s ({len(POLICY_CLAUSES)} clauses indexed)")
        print(f"  Claim: {claim_record['claim_id']} | claimed amount: Rs.{claim_record['claim_amount']:,}")

    images = load_sample_images()
    scenarios = {}
    for scenario, image_bytes in images.items():
        final_state = agent.invoke(
            {"claim_record": claim_record, "image_bytes": image_bytes}, config=config.runnable_config()
        )
        scenarios[scenario] = {
            "damage_assessment": final_state["damage_assessment"],
            "policy_citations": final_state["policy_citations"],
            "decision": final_state["decision"],
        }
        if verbose:
            va = final_state["damage_assessment"]
            d = final_state["decision"]
            print(f"\n  --- {scenario.replace('_', ' ').upper()} ---")
            print(f"    vision:    {va['damage_type']} (severity {va['severity']}/10, est. Rs.{va['estimated_repair_inr']:,})")
            print(f"    decision:  {d['decision']}  (confidence {d['confidence']:.2f})")
            print(f"    fraud:     {'FLAG - ' + d['fraud_signal_reason'] if d['fraud_signal'] else 'none'}")
            print(f"    clauses:   {', '.join(d['coverage_clause_ids'])}")

    total_time = time.time() - t0

    if verbose:
        print(f"\n  Done in {total_time:.1f}s.")
        if config.TRACING_ENABLED:
            print(f"  Traced to LangSmith project '{config.LANGSMITH_PROJECT}'.")
            print(f"  View traces: {config.langsmith_project_url()}")

    return {
        "pattern": PATTERN_NAME,
        "description": PATTERN_DESCRIPTION,
        "claim_record": claim_record,
        "scenarios": scenarios,
        "build_time_sec": build_time,
        "total_time_sec": total_time,
    }
