import streamlit as st
import requests
import json
import re
import time
from typing import List, Dict

st.set_page_config(
    page_title="AI Research Agent",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.hero {
    background: linear-gradient(135deg, #0d1117 0%, #161b22 60%, #1c2333 100%);
    border: 1px solid #30363d;
    border-radius: 16px;
    padding: 2.5rem 2rem 2rem;
    margin-bottom: 1.2rem;
    text-align: center;
}
.hero h1 { font-size: 2rem; font-weight: 700; color: #f0f6fc; margin: 0; }
.hero p  { color: #8b949e; margin: .5rem 0 0; font-size: .95rem; }
.hero .badge {
    display: inline-block; background: #1f3a5f; color: #79c0ff;
    font-size: .75rem; font-weight: 600; padding: 4px 12px;
    border-radius: 20px; border: 1px solid #388bfd; margin-top: .8rem;
}
.step-card {
    background: #161b22; border: 1px solid #30363d;
    border-radius: 10px; padding: .9rem 1.1rem; margin-bottom: .6rem;
}
.step-header {
    display: flex; align-items: center; gap: 10px; margin-bottom: .4rem;
}
.step-num {
    width: 24px; height: 24px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: .75rem; font-weight: 600; flex-shrink: 0;
}
.step-num.done    { background: #1f4e2e; color: #3fb950; }
.step-num.active  { background: #1f3a5f; color: #79c0ff; }
.step-num.pending { background: #21262d; color: #8b949e; }
.step-title { font-size: .9rem; font-weight: 500; color: #f0f6fc; }
.step-detail { font-size: .8rem; color: #8b949e; margin-left: 34px; }
.source-card {
    background: #161b22; border: 1px solid #30363d;
    border-left: 3px solid #388bfd; border-radius: 6px;
    padding: .6rem .9rem; margin-bottom: .5rem;
    font-size: .82rem; color: #8b949e;
}
.source-card a { color: #79c0ff; text-decoration: none; }
.source-card a:hover { text-decoration: underline; }
.report-box {
    background: #161b22; border: 1px solid #30363d;
    border-radius: 12px; padding: 1.4rem 1.6rem;
    color: #f0f6fc; font-size: .95rem; line-height: 1.8;
}
.tag { display: inline-block; background: #1c2d3f; color: #79c0ff;
       font-size: .72rem; padding: 3px 10px; border-radius: 20px; margin: 3px; }
.query-pill {
    display: inline-block; background: #21262d; color: #8b949e;
    border: 1px solid #30363d; font-size: .78rem;
    padding: 3px 10px; border-radius: 20px; margin: 3px;
}
</style>
""", unsafe_allow_html=True)

# ── Groq API ──────────────────────────────────────────────────────────────────
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

def groq_call(messages: List[Dict], temperature=0.3, max_tokens=2048) -> str:
    api_key = st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        st.error("⚠️ GROQ_API_KEY not found in Streamlit secrets.")
        st.stop()
    r = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": MODEL, "messages": messages,
              "temperature": temperature, "max_tokens": max_tokens},
        timeout=30,
    )
    if r.status_code != 200:
        st.error(f"Groq API error {r.status_code}: {r.text[:300]}")
        st.stop()
    return r.json()["choices"][0]["message"]["content"].strip()

# ── DuckDuckGo search (free, no key) ─────────────────────────────────────────
def ddg_search(query: str, max_results=4) -> List[Dict]:
    try:
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1,
                    "skip_disambig": 1, "no_redirect": 1},
            timeout=8, headers={"User-Agent": "research-agent/1.0"}
        )
        data = r.json()
        results = []
        # Abstract result
        if data.get("AbstractText") and data.get("AbstractURL"):
            results.append({
                "title": data.get("Heading", query),
                "url":   data["AbstractURL"],
                "snippet": data["AbstractText"][:300],
            })
        # Related topics
        for t in data.get("RelatedTopics", []):
            if len(results) >= max_results:
                break
            if isinstance(t, dict) and t.get("Text") and t.get("FirstURL"):
                results.append({
                    "title":   t.get("Text","")[:60],
                    "url":     t["FirstURL"],
                    "snippet": t.get("Text","")[:300],
                })
        return results
    except Exception:
        return []

def scrape_page(url: str, max_chars=1500) -> str:
    try:
        r = requests.get(url, timeout=6,
            headers={"User-Agent": "Mozilla/5.0 (compatible; research-agent/1.0)"})
        text = re.sub(r'<[^>]+>', ' ', r.text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:max_chars]
    except Exception:
        return ""

# ── Agent steps ───────────────────────────────────────────────────────────────
def plan_queries(topic: str, n_queries: int) -> List[str]:
    response = groq_call([
        {"role": "system", "content":
            "You are a research planner. Given a topic, output ONLY a JSON array "
            f"of {n_queries} specific search queries to research it thoroughly. "
            "No explanation, no markdown, just the JSON array of strings."},
        {"role": "user", "content": f"Topic: {topic}"},
    ], temperature=0.4, max_tokens=300)
    try:
        clean = re.sub(r"```json|```", "", response).strip()
        queries = json.loads(clean)
        return [str(q) for q in queries[:n_queries]]
    except Exception:
        # Fallback: extract quoted strings
        return re.findall(r'"([^"]{10,})"', response)[:n_queries] or [topic]

def synthesise_report(topic: str, sources: List[Dict], report_style: str) -> str:
    source_text = ""
    for i, s in enumerate(sources):
        source_text += f"\n\n[SOURCE {i+1}] {s['title']}\nURL: {s['url']}\n{s['content']}"

    style_instructions = {
        "Detailed report": "Write a detailed, well-structured report with sections: ## Summary, ## Key Findings, ## How It Works, ## Use Cases, ## Limitations. Use markdown formatting.",
        "Quick brief":     "Write a concise 3-paragraph brief covering: what it is, how it works, and why it matters. Keep it under 200 words.",
        "Bullet points":   "Write a bullet-point summary with clear sections: **What it is**, **How it works**, **Key benefits**, **Limitations**. Use markdown bullets.",
        "ELI5":            "Explain this topic as if talking to a curious 12-year-old. Use simple language, analogies, and real-world examples. No jargon.",
    }

    instruction = style_instructions.get(report_style, style_instructions["Detailed report"])

    return groq_call([
        {"role": "system", "content":
            f"You are an expert research analyst. {instruction} "
            "Base your answer on the provided sources. "
            "Always cite sources using [SOURCE N] notation. "
            "If sources are limited, use your knowledge but note it clearly."},
        {"role": "user", "content":
            f"Topic: {topic}\n\nSources:{source_text}\n\nWrite the report now:"},
    ], temperature=0.3, max_tokens=1500)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Agent settings")
    n_queries   = st.slider("Search queries to generate", 2, 6, 3)
    report_style = st.selectbox("Report style",
        ["Detailed report", "Quick brief", "Bullet points", "ELI5"])
    show_sources = st.toggle("Show raw sources", True)
    show_steps   = st.toggle("Show agent steps", True)
    st.markdown("---")
    st.markdown("### 💡 Example topics")
    examples = [
        "Mixture of Experts in LLMs",
        "How does RAG compare to fine-tuning?",
        "What is speculative decoding?",
        "Explain flash attention",
        "What are AI agents and how do they work?",
        "How does RLHF align language models?",
    ]
    for ex in examples:
        if st.button(ex, key=ex, use_container_width=True):
            st.session_state["topic"] = ex
    st.markdown("---")
    st.markdown("""**Stack**  
    Groq (llama3-70b) · DuckDuckGo free search  
    Streamlit · Python · requests
    """)
    st.caption("Built by Nimra · [GitHub](https://github.com/nimra-pixel)")

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>🔬 AI Research Agent</h1>
  <p>Give it a topic — it plans, searches, reads, and writes a full report</p>
  <span class="badge">⚡ Powered by Groq · llama3-70b · DuckDuckGo</span>
</div>
""", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Model", "llama3-70b")
c2.metric("Speed", "~300 tok/s")
c3.metric("Search", "DuckDuckGo (free)")
c4.metric("Cost", "$0.00")

st.markdown("<br>", unsafe_allow_html=True)

topic = st.text_input(
    "Research topic",
    value=st.session_state.get("topic", ""),
    placeholder="e.g. How does Mixture of Experts work in LLMs?",
    label_visibility="collapsed",
)

col_run, col_clear = st.columns([1, 5])
with col_run:
    run = st.button("🔬 Research", type="primary", use_container_width=True)
with col_clear:
    if st.button("Clear", use_container_width=False):
        st.session_state.pop("topic", None)
        st.rerun()

# ── Agent run ─────────────────────────────────────────────────────────────────
if run and topic.strip():
    st.markdown("---")

    # ── Step 1: Plan ──────────────────────────────────────────────────────────
    step_ph = st.empty()

    def render_steps(steps):
        html = ""
        for s in steps:
            num_class = {"done":"done","active":"active","pending":"pending"}.get(s["status"],"pending")
            icon = "✓" if s["status"]=="done" else ("⟳" if s["status"]=="active" else "○")
            html += f"""
            <div class="step-card">
              <div class="step-header">
                <div class="step-num {num_class}">{icon}</div>
                <div class="step-title">{s['title']}</div>
              </div>
              <div class="step-detail">{s.get('detail','')}</div>
            </div>"""
        step_ph.markdown(html, unsafe_allow_html=True)

    steps = [
        {"title": "Planning search queries",    "status": "active",  "detail": ""},
        {"title": "Searching the web",           "status": "pending", "detail": ""},
        {"title": "Reading sources",             "status": "pending", "detail": ""},
        {"title": "Synthesising report",         "status": "pending", "detail": ""},
    ]
    if show_steps: render_steps(steps)

    t0 = time.time()
    queries = plan_queries(topic, n_queries)
    steps[0]["status"]="done"
    steps[0]["detail"]=f"Generated {len(queries)} queries in {time.time()-t0:.1f}s"
    steps[1]["status"]="active"
    if show_steps: render_steps(steps)

    # ── Step 2: Search ────────────────────────────────────────────────────────
    t1 = time.time()
    all_results = []
    for q in queries:
        results = ddg_search(q, max_results=3)
        all_results.extend(results)

    # Deduplicate by URL
    seen, unique = set(), []
    for r in all_results:
        if r["url"] not in seen:
            seen.add(r["url"]); unique.append(r)
    all_results = unique[:10]

    steps[1]["status"]="done"
    steps[1]["detail"]=f"Found {len(all_results)} unique sources in {time.time()-t1:.1f}s"
    steps[2]["status"]="active"
    if show_steps: render_steps(steps)

    # ── Step 3: Scrape ────────────────────────────────────────────────────────
    t2 = time.time()
    sources = []
    for r in all_results[:6]:
        content = scrape_page(r["url"]) or r["snippet"]
        sources.append({
            "title":   r["title"],
            "url":     r["url"],
            "snippet": r["snippet"],
            "content": content,
        })

    steps[2]["status"]="done"
    steps[2]["detail"]=f"Read {len(sources)} pages in {time.time()-t2:.1f}s"
    steps[3]["status"]="active"
    if show_steps: render_steps(steps)

    # ── Step 4: Synthesise ────────────────────────────────────────────────────
    t3 = time.time()
    report = synthesise_report(topic, sources, report_style)
    steps[3]["status"]="done"
    steps[3]["detail"]=f"Report written in {time.time()-t3:.1f}s"
    if show_steps: render_steps(steps)

    total_time = round(time.time()-t0, 1)

    # ── Results ───────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"**📄 Research report** · _{report_style}_ · ⚡ {total_time}s total")
    st.markdown(f'<div class="report-box">', unsafe_allow_html=True)
    st.markdown(report)
    st.markdown('</div>', unsafe_allow_html=True)

    # Queries used
    st.markdown("**🔍 Queries used**")
    q_html = "".join(f"<span class='query-pill'>{q}</span>" for q in queries)
    st.markdown(q_html, unsafe_allow_html=True)

    # Sources
    if show_sources and sources:
        st.markdown(f"**🌐 Sources ({len(sources)})**")
        for i, s in enumerate(sources):
            st.markdown(f"""
            <div class="source-card">
              <strong>[{i+1}]</strong> <a href="{s['url']}" target="_blank">{s['title'][:80]}</a><br>
              <span>{s['snippet'][:180]}...</span>
            </div>""", unsafe_allow_html=True)

    # Download
    st.download_button(
        "⬇️ Download report (.md)",
        data=f"# Research Report: {topic}\n\n{report}\n\n---\n**Queries:** {', '.join(queries)}",
        file_name=f"research_{topic[:30].replace(' ','_')}.md",
        mime="text/markdown",
    )

elif run and not topic.strip():
    st.warning("Please enter a research topic.")
