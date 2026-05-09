# 🔍 FactCheck Agent

> Automated PDF fact-checking powered by **Gemini 2.0 Flash** + **Google Search grounding** — 100% free API tier.

Upload any PDF and the agent will:
1. **Extract** every verifiable claim (stats, dates, financials, figures)
2. **Search the live web** via Google Search grounding to cross-reference each claim
3. **Report** each claim as `VERIFIED`, `INACCURATE`, `FALSE`, or `UNVERIFIABLE`

---

## 🚀 Live Demo

> **[→ Open the deployed app](https://your-app.streamlit.app)**  
> *(Update this link after deploying)*

---

## 🆓 Free API — No Credit Card Needed

This app uses **Google Gemini 2.0 Flash** which has a generous free tier:
- **15 requests/minute** free
- **1 million tokens/day** free
- Get your key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) — no credit card required

---

## 🛠️ Tech Stack

| Layer | Tool |
|---|---|
| Frontend | Streamlit |
| LLM | Gemini 2.0 Flash (`gemini-2.0-flash`) |
| Live web verification | Google Search grounding (built into Gemini) |
| PDF parsing | Gemini File API (native PDF understanding) |
| Deployment | Streamlit Cloud (free) |

---

## 📁 Project Structure

```
factcheck-gemini/
├── app.py                   # Main Streamlit application
├── requirements.txt         # Python dependencies (3 packages)
├── .streamlit/
│   ├── config.toml          # Dark theme + server config
│   └── secrets.toml         # API key (NOT committed to git)
├── .gitignore
└── README.md
```

---

## 🏃 Run Locally

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/factcheck-gemini.git
cd factcheck-gemini

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your free API key
mkdir -p .streamlit
echo 'GEMINI_API_KEY = "AIza_YOUR_KEY"' > .streamlit/secrets.toml

# 4. Run
streamlit run app.py
```

---

## ☁️ Deploy to Streamlit Cloud (free, ~2 minutes)

1. Push this repo to **GitHub** (secrets.toml is gitignored — safe)
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Select your repo → branch `main` → file `app.py`
4. Click **Advanced settings → Secrets**, paste:
   ```toml
   GEMINI_API_KEY = "AIza_YOUR_KEY_HERE"
   ```
5. Click **Deploy** — live in ~60 seconds ✅

---

## 🧠 How It Works

### Step 1 — PDF Upload & Claim Extraction
The PDF is uploaded to the **Gemini File API**, which gives Gemini native access to the full document. The model reads it and returns structured JSON of every verifiable claim:

```json
[
  { "id": 1, "claim": "Global EV sales grew 35% in 2023", "category": "statistic", "context": "..." }
]
```

### Step 2 — Live Web Verification with Google Search
Each claim is sent to Gemini 2.0 Flash with **Google Search grounding** enabled. The model autonomously searches the web and returns:

```json
[
  {
    "id": 1,
    "verdict": "INACCURATE",
    "confidence": "HIGH",
    "explanation": "EV sales grew ~31% in 2023, not 35% as claimed...",
    "correct_fact": "Global EV sales grew approximately 31% in 2023",
    "source": "IEA Global EV Outlook 2024"
  }
]
```

### Step 3 — Visual Report
Results are displayed with color-coded badges, corrected facts, source links, summary stats, and a downloadable JSON report.

---

## ⚠️ Verdict Definitions

| Verdict | Meaning |
|---|---|
| ✅ **VERIFIED** | Claim matches current reliable web data |
| ⚠️ **INACCURATE** | Claim has basis but figures/dates are wrong or outdated |
| ✗ **FALSE** | Claim is demonstrably wrong with no supporting evidence |
| ? **UNVERIFIABLE** | Cannot find reliable data to confirm or deny |

---

## 📋 Requirements

- Python 3.9+
- Free Gemini API key from [aistudio.google.com](https://aistudio.google.com/app/apikey)

---

## 📄 License

MIT
