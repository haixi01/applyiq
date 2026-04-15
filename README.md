# ApplyIQ — AI Job Application Agent

Paste a resume and a job description → ApplyIQ parses both, researches the company via web search, and generates a tailored application package.

Built for **14-789 AI in Business Modeling** (CMU, Spring 2026) — Group 7.

---

## Table of Contents

- [Demo Videos](#demo-videos)
- [Architecture](#architecture)
- [Local Setup](#local-setup)
- [Kubernetes Deployment (GKE)](#kubernetes-deployment-gke)
- [Files](#files)

---

## Demo Videos

| Video | Link |
|---|---|
| Task II — Langflow Proof-of-Concept (~5 min) | https://youtu.be/mLL-slC-Jbc |
| Extra Credit Part 1 — Standalone Streamlit GUI (~2 min) | https://youtu.be/5Y1jWb1rFqY |
| Extra Credit Part 2 — Kubernetes Deployment (~5 min) | https://youtu.be/maH4x3W98nI |

---

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

---

## Local Setup

**Prerequisites:** Python 3.10+, [Langflow](https://docs.langflow.org/) v1.5+, a Google Gemini API key.

### 1. Start Langflow

```bash
LANGFLOW_AUTO_LOGIN=true LANGFLOW_SKIP_AUTH_AUTO_LOGIN=true langflow run
```

Then open the Langflow UI (default `http://localhost:7861`):
- **Import** `langflow_flow.json` (drag and drop onto the home page)
- Go to **Settings → Global Variables → Add New**, name it `GOOGLE_API_KEY`, paste your Gemini key
- Note the **flow ID** from the URL bar

### 2. Run the Streamlit app

```bash
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:
```properties
LANGFLOW_BASE_URL=http://127.0.0.1:7861
LANGFLOW_FLOW_ID=<your-flow-id>
LANGFLOW_USERNAME=langflow
LANGFLOW_PASSWORD=langflow
```

```bash
streamlit run app.py
```

Open `http://localhost:8501`, paste a resume and job description, click **Generate Package**.

---

## Kubernetes Deployment (GKE)

**Prerequisites:** Docker, `gcloud` CLI, `kubectl`, a GCP project with GKE enabled.

### 1. Build and push Docker images

```bash
# Mac M-chip: must build for linux/amd64
docker buildx create --name applyiq-builder --use

docker buildx build --platform linux/amd64 --provenance=false \
  -f Dockerfile.langflow -t <dockerhub-user>/applyiq-langflow:latest --push .

docker buildx build --platform linux/amd64 --provenance=false \
  -f Dockerfile.streamlit -t <dockerhub-user>/applyiq-streamlit:latest --push .
```

### 2. Create a GKE Autopilot cluster

```bash
gcloud container clusters create-auto applyiq-cluster \
  --region us-central1 --project <gcp-project>

gcloud container clusters get-credentials applyiq-cluster \
  --region us-central1 --project <gcp-project>
```

### 3. Create the API key secret

```bash
kubectl create secret generic applyiq-secret \
  --from-literal=GOOGLE_API_KEY=<your-gemini-api-key>
```

### 4. Deploy

```bash
kubectl apply -f langflow-deployment.yaml
kubectl apply -f langflow-service.yaml
kubectl apply -f streamlit-deployment.yaml
kubectl apply -f streamlit-service.yaml
```

### 5. Get the external IP

```bash
kubectl get service streamlit-service
# Wait for EXTERNAL-IP to populate, then open http://<EXTERNAL-IP>
```

Langflow runs as an internal ClusterIP service (port 7860). Streamlit is exposed via a LoadBalancer on port 80. The `GOOGLE_API_KEY` is stored as a Kubernetes secret and injected into the Langflow pod at startup.

---

## Files

| File | Description |
|---|---|
| `app.py` | Streamlit frontend — JWT auth, PDF upload, calls Langflow REST API |
| `langflow_flow.json` | Exported Langflow pipeline (15 nodes, 3 branches) |
| `requirements.txt` | Python dependencies |
| `Dockerfile.langflow` | Langflow image with flow baked in |
| `Dockerfile.streamlit` | Streamlit frontend image |
| `entrypoint.sh` | Langflow startup script — injects GOOGLE_API_KEY as a global variable |
| `langflow-deployment.yaml` | K8s Deployment for Langflow |
| `langflow-service.yaml` | K8s ClusterIP Service for Langflow (internal) |
| `streamlit-deployment.yaml` | K8s Deployment for Streamlit |
| `streamlit-service.yaml` | K8s LoadBalancer Service for Streamlit (external) |
| `applyiq-secret.yaml` | K8s Secret template for GOOGLE_API_KEY |
| `.env.example` | Environment variable template for local dev |