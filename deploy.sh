#!/usr/bin/env bash
# =============================================================================
# ApplyIQ — GKE Deployment Script
# Extra Credit Part 2 | 14-789 AI in Business Modeling
# =============================================================================
# Run sections manually in order. Do NOT run this whole script at once.
# Each section is independent and idempotent.
# =============================================================================

# ── FILL THESE IN BEFORE STARTING ────────────────────────────────────────────
DOCKER_USER="haixi01"
GCP_PROJECT="lucid-office-449617-m3"    # or cloud-computing-470721
GCP_REGION="us-central1"
CLUSTER_NAME="applyiq-cluster"
GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY_HERE"
# ─────────────────────────────────────────────────────────────────────────────


# =============================================================================
# STEP 1 — Set up your project directory
# =============================================================================
# Your project root must contain:
#   app.py
#   requirements.txt
#   langflow_flow.json
#   Dockerfile.langflow
#   Dockerfile.streamlit
#   entrypoint.sh
#   manifests/  (all 5 yaml files)
#
# cd ~/Desktop/AI_Bus_Models/project/


# =============================================================================
# STEP 2 — Build and push Docker images (Mac M-chip: must use linux/amd64)
# =============================================================================

# Ensure buildx builder exists
docker buildx create --name applyiq-builder --use 2>/dev/null || docker buildx use applyiq-builder

# Build and push Langflow image (~5-10 min on first build)
docker buildx build \
  --platform linux/amd64 \
  --provenance=false \
  -f Dockerfile.langflow \
  -t ${DOCKER_USER}/applyiq-langflow:latest \
  --push \
  .

# Build and push Streamlit image (~2-3 min)
docker buildx build \
  --platform linux/amd64 \
  --provenance=false \
  -f Dockerfile.streamlit \
  -t ${DOCKER_USER}/applyiq-streamlit:latest \
  --push \
  .

# Verify both images are on Docker Hub
echo "Verify at: https://hub.docker.com/u/${DOCKER_USER}"


# =============================================================================
# STEP 3 — Create GKE Autopilot cluster
# =============================================================================

gcloud config set project ${GCP_PROJECT}

# Create cluster (~5 min)
gcloud container clusters create-auto ${CLUSTER_NAME} \
  --region ${GCP_REGION} \
  --project ${GCP_PROJECT}

# Get credentials
gcloud container clusters get-credentials ${CLUSTER_NAME} \
  --region ${GCP_REGION} \
  --project ${GCP_PROJECT}

# Verify kubectl is connected
kubectl get nodes


# =============================================================================
# STEP 4 — Create the GOOGLE_API_KEY secret
# =============================================================================

# Base64-encode the key
ENCODED_KEY=$(echo -n "${GOOGLE_API_KEY}" | base64)
echo "Encoded key: ${ENCODED_KEY}"

# Edit manifests/applyiq-secret.yaml and replace REPLACE_WITH_BASE64_ENCODED_KEY
# with the value printed above, then:
kubectl apply -f manifests/applyiq-secret.yaml

# Verify secret was created
kubectl get secret applyiq-secret


# =============================================================================
# STEP 5 — Deploy all Kubernetes resources
# =============================================================================

kubectl apply -f manifests/langflow-deployment.yaml
kubectl apply -f manifests/langflow-service.yaml
kubectl apply -f manifests/streamlit-deployment.yaml
kubectl apply -f manifests/streamlit-service.yaml

# Check deployments are created
kubectl get deployments


# =============================================================================
# STEP 6 — Wait for pods to be Running
# =============================================================================

# Watch pods (Ctrl+C when all are Running)
# Note: Langflow pod takes 2-4 min to become Ready (heavy startup + flow loading)
kubectl get pods -w

# Once stable, check final status:
kubectl get pods
kubectl get services

# The streamlit-service EXTERNAL-IP will show <pending> for ~1-2 min, then get an IP.
# Run this until you see a real IP:
kubectl get service streamlit-service --watch


# =============================================================================
# STEP 7 — Verify Langflow received GOOGLE_API_KEY (optional sanity check)
# =============================================================================

# Port-forward to Langflow to check the UI
kubectl port-forward service/langflow-service 7860:7860 &
# Open http://localhost:7860 in browser
# Go to Settings → Global Variables → confirm GOOGLE_API_KEY is listed
# Kill the port-forward:
# kill %1


# =============================================================================
# STEP 8 — Smoke test the Streamlit app
# =============================================================================

# Get the external IP
EXTERNAL_IP=$(kubectl get service streamlit-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "Streamlit app: http://${EXTERNAL_IP}"

# Open in browser — paste a resume and job description to verify end-to-end


# =============================================================================
# STEP 9 — Commands to show during your 5-min video recording
# =============================================================================
#
# Screen 1 — Show all pods Running:
kubectl get pods
#
# Screen 2 — Show services + external IP:
kubectl get services
#
# Screen 3 — Port-forward to show Langflow UI (to satisfy "underlying services" requirement):
kubectl port-forward service/langflow-service 7860:7860
# (open http://localhost:7860 in browser, show Langflow flow canvas)
#
# Screen 4 — Show Streamlit in browser with EXTERNAL-IP visible in URL bar
# Navigate to: http://<EXTERNAL-IP>
#
# Screen 5 — Run a live end-to-end demo (paste resume + job desc, generate package)


# =============================================================================
# TROUBLESHOOTING
# =============================================================================
#
# Pod stuck in Pending:
#   kubectl describe pod <pod-name>
#   # GKE Autopilot auto-provisions nodes — Langflow needs 1Gi+ RAM, give it a few min
#
# Langflow pod CrashLoopBackOff:
#   kubectl logs <langflow-pod-name>
#   # Usually a startup timeout; bump initialDelaySeconds in langflow-deployment.yaml
#
# Streamlit gets 403 from Langflow:
#   kubectl logs <streamlit-pod-name>
#   # Check LANGFLOW_AUTO_LOGIN=true is in langflow-deployment.yaml env section
#
# Need to force re-pull latest image (after a new push):
#   kubectl rollout restart deployment/langflow
#   kubectl rollout restart deployment/streamlit-app
#
# Delete everything and start clean:
#   kubectl delete -f manifests/
#   kubectl delete secret applyiq-secret

echo "Done."
