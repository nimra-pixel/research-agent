# 🔬 AI Research Agent

An agentic AI system that takes a topic, autonomously plans search queries, reads web sources, and synthesises a structured research report — all in under 30 seconds.

🚀 **[Live Demo →](https://your-app.streamlit.app)**

---

## How it works

```
Topic → Planner (Groq) → Search queries → DuckDuckGo → Scrape pages → Synthesiser (Groq) → Report
```

1. **Plan** — Groq (llama3-70b) breaks your topic into 3–6 targeted search queries
2. **Search** — DuckDuckGo free API finds relevant pages for each query
3. **Read** — Agent scrapes and extracts text from top results
4. **Synthesise** — Groq reads all sources and writes a structured report with citations

## Features

- 4 report styles: detailed report, quick brief, bullet points, ELI5
- Cites sources with [SOURCE N] notation
- Shows agent reasoning steps in real time
- Download report as markdown
- Runs in ~15–30 seconds end to end

## Stack

| Component | Technology |
|---|---|
| LLM | Groq llama3-70b-8192 (free tier) |
| Search | DuckDuckGo Instant Answer API (free, no key) |
| Frontend | Streamlit |
| Language | Python |

## Run locally

```bash
git clone https://github.com/nimra-pixel/research-agent
cd research-agent
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

mkdir -p .streamlit
echo '[secrets]\nGROQ_API_KEY = "gsk_your_key_here"' > .streamlit/secrets.toml

streamlit run app.py
```

Get a free Groq API key at **console.groq.com**

## Deploy (Streamlit Cloud)

1. Push to GitHub
2. Go to share.streamlit.io → New app
3. Add secret: `GROQ_API_KEY = "gsk_..."`
4. Deploy

---

Built by [Nimra](https://linkedin.com/in/yourprofile) ·  
