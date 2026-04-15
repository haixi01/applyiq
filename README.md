# ApplyIQ — AI Job Application Agent

Paste a resume and a job description → ApplyIQ parses both, researches the company via web search, and generates a tailored application package.

Built for **14-789 AI in Business Modeling** (CMU, Spring 2026) — Group 7.

## Architecture

```
Streamlit GUI (app.py)          Langflow Pipeline (15 nodes)
┌──────────────────┐   REST    ┌────────────────────────────────┐
│ Resume input     │──────────▶│ Resume Parser LLM              │
│ Job desc input   │  /api/v1/ │ Job Desc Parser LLM            │
│ Results display  │   run     │ Company Enrichment (Web Search) │
└──────────────────┘◀──────────│ Match & Tailor LLM → Output    │
                               └────────────────────────────────┘
```

Three parallel branches (resume parsing, job parsing, company enrichment) merge into a final Match & Tailor stage that produces the application package.

## Setup

**Prerequisites:** Python 3.10+, [Langflow](https://docs.langflow.org/) v1.5+, a Google Gemini API key.

### 1. Start Langflow

```bash
LANGFLOW_AUTO_LOGIN=true LANGFLOW_SKIP_AUTH_AUTO_LOGIN=true langflow run
```

Then open the Langflow UI (default `http://localhost:7861`):
- **Import** `langflow_flow.json` (drag and drop onto the home page)
- Go to **Settings → Global Variables → Add New**, name it `GOOGLE_API_KEY`, paste your Gemini key
- Open the flow and note the **flow ID** from the URL bar

### 2. Run the Streamlit app

```bash
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your values:
```properties
LANGFLOW_BASE_URL=http://127.0.0.1:7861
LANGFLOW_FLOW_ID=<your-flow-id>
LANGFLOW_USERNAME=langflow
LANGFLOW_PASSWORD=langflow
```

```bash
streamlit run app.py
```

Open `http://localhost:8501`, paste a resume and job description, and click **Generate Application Package**.

## Files

| File | Description |
|---|---|
| `app.py` | Streamlit frontend — authenticates and calls Langflow REST API |
| `langflow_flow.json` | Exported Langflow pipeline (15 nodes) |
| `requirements.txt` | Python dependencies |
| `.env.example` | Environment variable template |