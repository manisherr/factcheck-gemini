import streamlit as st
import google.generativeai as genai
import json
import re
import base64
import tempfile
import os
import time
import pathlib
import httpx
from datetime import datetime

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FactCheck Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
#MainMenu {visibility:hidden;} footer{visibility:hidden;} header{visibility:hidden;}
.stApp { background:#0a0a0f; color:#e8e8f0; }
.block-container { max-width:900px; padding:2rem 1.5rem; }

.app-header { text-align:center; padding:2.5rem 0 2rem; border-bottom:1px solid #1e1e2e; margin-bottom:2rem; }
.app-header h1 { font-size:2.4rem; font-weight:600; letter-spacing:-0.02em; color:#f0f0ff; margin-bottom:0.4rem; }
.app-header .tagline { font-size:0.9rem; color:#6b6b8a; font-family:'IBM Plex Mono',monospace; letter-spacing:0.04em; }
.accent { color:#4f8ef7; }

.badge-verified   { display:inline-block; background:#0d2818; color:#4ade80; border:1px solid #166534; padding:3px 10px; border-radius:20px; font-size:0.72rem; font-family:'IBM Plex Mono',monospace; font-weight:600; letter-spacing:0.05em; text-transform:uppercase; }
.badge-inaccurate { display:inline-block; background:#1f1200; color:#fb923c; border:1px solid #92400e; padding:3px 10px; border-radius:20px; font-size:0.72rem; font-family:'IBM Plex Mono',monospace; font-weight:600; letter-spacing:0.05em; text-transform:uppercase; }
.badge-false      { display:inline-block; background:#1f0808; color:#f87171; border:1px solid #991b1b; padding:3px 10px; border-radius:20px; font-size:0.72rem; font-family:'IBM Plex Mono',monospace; font-weight:600; letter-spacing:0.05em; text-transform:uppercase; }
.badge-unverifiable { display:inline-block; background:#141428; color:#94a3b8; border:1px solid #334155; padding:3px 10px; border-radius:20px; font-size:0.72rem; font-family:'IBM Plex Mono',monospace; font-weight:600; letter-spacing:0.05em; text-transform:uppercase; }

.claim-card { background:#111120; border:1px solid #1e1e35; border-radius:10px; padding:1.2rem 1.4rem; margin-bottom:1rem; }
.claim-card.verified   { border-left:3px solid #4ade80; }
.claim-card.inaccurate { border-left:3px solid #fb923c; }
.claim-card.false      { border-left:3px solid #f87171; }
.claim-card.unverifiable { border-left:3px solid #475569; }
.claim-text    { font-size:0.92rem; color:#c8c8e0; line-height:1.55; margin:0.4rem 0 0.8rem; font-style:italic; }
.verdict-detail{ font-size:0.85rem; color:#8888aa; line-height:1.5; }
.correct-fact  { font-size:0.85rem; color:#4ade80; margin-top:0.5rem; padding:0.4rem 0.7rem; background:#0a1f12; border-radius:6px; }
.source-link   { font-size:0.78rem; color:#4f8ef7; font-family:'IBM Plex Mono',monospace; margin-top:0.4rem; word-break:break-all; }

.stats-row { display:flex; gap:1rem; margin:1.5rem 0; justify-content:center; flex-wrap:wrap; }
.stat-box  { background:#111120; border:1px solid #1e1e35; border-radius:10px; padding:1rem 1.5rem; text-align:center; min-width:110px; }
.stat-number { font-size:1.8rem; font-weight:600; font-family:'IBM Plex Mono',monospace; }
.stat-label  { font-size:0.72rem; color:#6b6b8a; text-transform:uppercase; letter-spacing:0.06em; margin-top:2px; }
.green{color:#4ade80;} .orange{color:#fb923c;} .red{color:#f87171;} .gray{color:#64748b;} .blue{color:#4f8ef7;}

.stProgress > div > div > div { background:#4f8ef7 !important; }
.stButton > button { background:#4f8ef7; color:white; border:none; border-radius:8px; padding:0.6rem 1.8rem; font-weight:500; font-size:0.92rem; cursor:pointer; }
.stButton > button:hover { opacity:0.88; background:#4f8ef7; color:white; }
hr { border-color:#1e1e2e; margin:1.5rem 0; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
  <h1>🔍 <span class="accent">FactCheck</span> Agent</h1>
  <p class="tagline">// automated truth verification · powered by gemini 2.0 flash + google search</p>
</div>
""", unsafe_allow_html=True)

# ── API Key input ─────────────────────────────────────────────────────────────
def get_api_key():
    key = st.secrets.get("GEMINI_API_KEY", None)
    if key:
        return key
    with st.sidebar:
        st.markdown("### 🔑 Gemini API Key")
        st.markdown("[Get free key →](https://aistudio.google.com/app/apikey)", unsafe_allow_html=True)
        key = st.text_input("Paste your key here", type="password")
    return key or None

api_key = get_api_key()
if not api_key:
    st.info("👈 **Add your free Gemini API key in the sidebar** — [Get one free at aistudio.google.com](https://aistudio.google.com/app/apikey)")
    st.stop()

# Configure Gemini
genai.configure(api_key=api_key)

# ── Prompts ───────────────────────────────────────────────────────────────────
EXTRACT_PROMPT = """You are an expert claim extractor. Read this document carefully and extract every verifiable factual claim — statistics, percentages, dates, financial figures, technical specifications, market sizes, growth rates, rankings, and named assertions.

Return ONLY a valid JSON array (no markdown fences, no extra text) with this exact shape:
[
  {
    "id": 1,
    "claim": "exact quote or close paraphrase of the claim from the document",
    "category": "statistic|date|financial|technical|ranking|other",
    "context": "one sentence of surrounding context"
  }
]

Extract 5-20 claims. Focus on specific, verifiable assertions. Skip vague opinions."""

VERIFY_PROMPT = """You are a rigorous fact-checker. For each claim below, use your knowledge and web grounding to verify its accuracy.

Claims to verify:
{claims_json}

Return ONLY a valid JSON array (no markdown fences, no extra text) with this exact shape:
[
  {{
    "id": <same id as input>,
    "verdict": "VERIFIED|INACCURATE|FALSE|UNVERIFIABLE",
    "confidence": "HIGH|MEDIUM|LOW",
    "explanation": "2-3 sentence explanation of your finding with specific data",
    "correct_fact": "the accurate figure/date/fact if the claim is wrong, else null",
    "source": "source name or URL if found, else null"
  }}
]

Verdict definitions:
- VERIFIED: claim matches current reliable data
- INACCURATE: claim has a kernel of truth but key figures/dates are wrong or outdated  
- FALSE: claim is demonstrably wrong with no supporting evidence
- UNVERIFIABLE: cannot find reliable data to confirm or deny

Be rigorous. Outdated statistics count as INACCURATE. Provide specific correct figures where possible."""


# ── Core functions ────────────────────────────────────────────────────────────
def extract_claims(pdf_bytes: bytes) -> list[dict]:
    """Upload PDF to Gemini and extract claims."""
    model = genai.GenerativeModel("gemini-2.0-flash")

    # Write to temp file and upload
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        tmp_path = f.name

    try:
        uploaded = genai.upload_file(tmp_path, mime_type="application/pdf")
        # Wait for processing
        for _ in range(30):
            if uploaded.state.name == "ACTIVE":
                break
            time.sleep(2)
            uploaded = genai.get_file(uploaded.name)

        response = model.generate_content([EXTRACT_PROMPT, uploaded])
        raw = response.text.strip()
    finally:
        os.unlink(tmp_path)

    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        raw = match.group(0)
    return json.loads(raw)


def verify_claims(claims: list[dict]) -> list[dict]:
    """Verify claims using Gemini 2.0 Flash with Google Search grounding."""
    model = genai.GenerativeModel(
        "gemini-2.0-flash",
        tools=[{"google_search": {}}],          # Google Search grounding tool
    )

    prompt = VERIFY_PROMPT.format(claims_json=json.dumps(claims, indent=2))
    response = model.generate_content(prompt)
    raw = response.text.strip()

    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        raw = match.group(0)
    return json.loads(raw)


def merge(claims: list[dict], verdicts: list[dict]) -> list[dict]:
    vm = {v["id"]: v for v in verdicts}
    return [{**c, **vm.get(c["id"], {})} for c in claims]


def badge(verdict: str) -> str:
    v = verdict.upper()
    if v == "VERIFIED":    return '<span class="badge-verified">✓ Verified</span>'
    if v == "INACCURATE":  return '<span class="badge-inaccurate">⚠ Inaccurate</span>'
    if v == "FALSE":       return '<span class="badge-false">✗ False</span>'
    return '<span class="badge-unverifiable">? Unverifiable</span>'


def render_card(item: dict):
    verdict = item.get("verdict", "UNVERIFIABLE").upper()
    css = verdict.lower() if verdict in ("VERIFIED","INACCURATE","FALSE") else "unverifiable"
    correct_html = f'<div class="correct-fact">✓ Correct fact: {item["correct_fact"]}</div>' if item.get("correct_fact") else ""
    source_html  = f'<div class="source-link">📎 {item["source"]}</div>' if item.get("source") else ""
    conf = item.get("confidence","")
    conf_txt = f" · {conf} confidence" if conf else ""

    st.markdown(f"""
    <div class="claim-card {css}">
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
        {badge(verdict)}
        <span style="font-size:0.75rem;color:#6b6b8a;font-family:'IBM Plex Mono',monospace;text-transform:uppercase;letter-spacing:0.04em;">{item.get('category','')}{conf_txt}</span>
      </div>
      <p class="claim-text">"{item.get('claim','')}"</p>
      <div class="verdict-detail">{item.get('explanation','')}</div>
      {correct_html}{source_html}
    </div>
    """, unsafe_allow_html=True)


# ── Upload UI ─────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    uploaded = st.file_uploader("Upload PDF", type=["pdf"], label_visibility="collapsed")
    if uploaded:
        st.caption(f"📄 **{uploaded.name}** · {uploaded.size/1024:.1f} KB")

if uploaded and st.button("🔍  Run Fact-Check", use_container_width=False):
    pdf_bytes = uploaded.read()
    st.markdown("---")

    # Step 1 – Extract
    with st.spinner("📖  Reading PDF & extracting claims..."):
        try:
            claims = extract_claims(pdf_bytes)
        except Exception as e:
            st.error(f"Extraction failed: {e}")
            st.stop()

    st.success(f"✅ Extracted **{len(claims)}** verifiable claims — now searching the web...")

    # Step 2 – Verify
    progress = st.progress(0, text="Verifying via Google Search grounding...")
    try:
        verdicts = verify_claims(claims)
        progress.progress(100, text="Done!")
    except Exception as e:
        st.error(f"Verification failed: {e}")
        st.stop()

    results = merge(claims, verdicts)

    # ── Summary ───────────────────────────────────────────────────────────────
    counts = {"VERIFIED":0,"INACCURATE":0,"FALSE":0,"UNVERIFIABLE":0}
    for r in results:
        v = r.get("verdict","UNVERIFIABLE").upper()
        counts[v] = counts.get(v,0) + 1
    flagged = counts["INACCURATE"] + counts["FALSE"]

    st.markdown(f"""
    <div class="stats-row">
      <div class="stat-box"><div class="stat-number green">{counts['VERIFIED']}</div><div class="stat-label">Verified</div></div>
      <div class="stat-box"><div class="stat-number orange">{counts['INACCURATE']}</div><div class="stat-label">Inaccurate</div></div>
      <div class="stat-box"><div class="stat-number red">{counts['FALSE']}</div><div class="stat-label">False</div></div>
      <div class="stat-box"><div class="stat-number gray">{counts['UNVERIFIABLE']}</div><div class="stat-label">Unverifiable</div></div>
      <div class="stat-box"><div class="stat-number blue">{flagged}</div><div class="stat-label">Flagged</div></div>
    </div>
    """, unsafe_allow_html=True)

    if flagged > 0:
        st.error(f"⚠️  **{flagged} claim(s)** flagged as inaccurate or false.")
    else:
        st.success("✅  All verifiable claims appear accurate.")

    st.markdown("---")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tabs = st.tabs(["All","🔴 Flagged","✅ Verified","⚠️ Inaccurate","✗ False","? Unverifiable"])
    filters = {0:None,1:["INACCURATE","FALSE"],2:["VERIFIED"],3:["INACCURATE"],4:["FALSE"],5:["UNVERIFIABLE"]}
    for i, tab in enumerate(tabs):
        with tab:
            f = filters[i]
            shown = [r for r in results if f is None or r.get("verdict","UNVERIFIABLE").upper() in f]
            if not shown:
                st.caption("No claims in this category.")
            for item in shown:
                render_card(item)

    # ── Download ──────────────────────────────────────────────────────────────
    st.markdown("---")
    report = {"file": uploaded.name, "timestamp": datetime.utcnow().isoformat()+"Z", "summary": counts, "results": results}
    st.download_button("⬇️  Download Report (JSON)", json.dumps(report, indent=2),
                       file_name=f"factcheck_{uploaded.name.replace('.pdf','')}.json", mime="application/json")

elif not uploaded:
    st.markdown("""
    <div style="text-align:center;padding:3rem 0;color:#4a4a6a;">
      <div style="font-size:3rem;margin-bottom:1rem;">📄</div>
      <p style="font-size:0.9rem;font-family:'IBM Plex Mono',monospace;">Upload a PDF above to begin</p>
      <p style="font-size:0.8rem;margin-top:0.5rem;color:#3a3a5a;">Reports · whitepapers · marketing decks · articles</p>
    </div>
    """, unsafe_allow_html=True)
