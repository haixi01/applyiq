#!/bin/bash
set -e

echo "=== ApplyIQ Langflow Entrypoint ==="

# Start Langflow in background
langflow run --host 0.0.0.0 --port 7860 &
LANGFLOW_PID=$!

# Wait for Langflow health endpoint
echo "Waiting for Langflow to become ready..."
ATTEMPTS=0
MAX_ATTEMPTS=60
until curl -sf http://localhost:7860/health > /dev/null 2>&1; do
  ATTEMPTS=$((ATTEMPTS + 1))
  if [ $ATTEMPTS -ge $MAX_ATTEMPTS ]; then
    echo "ERROR: Langflow did not become ready after ${MAX_ATTEMPTS} attempts. Exiting."
    kill $LANGFLOW_PID 2>/dev/null
    exit 1
  fi
  sleep 3
done
echo "Langflow is ready."

# Inject GOOGLE_API_KEY as a Langflow global variable
if [ -n "$GOOGLE_API_KEY" ]; then
  echo "Injecting GOOGLE_API_KEY as Langflow global variable..."

  # Get auth token (auto-login is enabled, so any credentials work)
  TOKEN=$(curl -s -X POST http://localhost:7860/api/v1/login \
    -d "username=langflow&password=langflow" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))" 2>/dev/null || echo "")

  if [ -n "$TOKEN" ]; then
    # Upsert: try to create; ignore conflict (409) if it already exists
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
      -X POST http://localhost:7860/api/v1/variables/ \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"name\":\"GOOGLE_API_KEY\",\"value\":\"${GOOGLE_API_KEY}\",\"type\":\"Credential\",\"default_fields\":[]}")

    if [ "$HTTP_STATUS" = "201" ] || [ "$HTTP_STATUS" = "200" ]; then
      echo "GOOGLE_API_KEY global variable set successfully (status $HTTP_STATUS)."
    elif [ "$HTTP_STATUS" = "409" ]; then
      echo "GOOGLE_API_KEY already exists — skipping (status 409)."
    else
      echo "Warning: Unexpected status $HTTP_STATUS when setting GOOGLE_API_KEY."
    fi
  else
    echo "Warning: Could not obtain auth token. GOOGLE_API_KEY not injected."
  fi
else
  echo "Warning: GOOGLE_API_KEY env var not set. Skipping global variable injection."
fi

echo "=== Langflow running (PID $LANGFLOW_PID). Handing off. ==="
wait $LANGFLOW_PID
