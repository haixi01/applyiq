"""
ApplyIQ — AI Job Application Agent
Standalone GUI that connects to a Langflow backend.
"""

import os
import json
import requests
import streamlit as st
# Load .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
LANGFLOW_BASE_URL = os.getenv("LANGFLOW_BASE_URL", "http://127.0.0.1:7860")
FLOW_ID = os.getenv("LANGFLOW_FLOW_ID", "9dd9a257-0e88-4397-bd19-1a9b51f1f23d")

# Node IDs inside the Langflow graph (from the exported JSON)
RESUME_NODE_ID = "TextInput-t7Cut"
JOB_NODE_ID = "TextInput-UGDxh"

# ---------------------------------------------------------------------------
# Langflow API helper
# ---------------------------------------------------------------------------

def _get_session() -> tuple[requests.Session, str]:
    """Return an authenticated requests.Session and a label for the sidebar.

    The session preserves cookies set during login (which Langflow uses
    for API auth) AND sends the Bearer token in the header as a belt-and-
    suspenders approach.

    Returns (session, auth_label).
    """
    session = requests.Session()

    # 1. API key
    api_key = os.getenv("LANGFLOW_API_KEY")
    if api_key:
        session.headers["x-api-key"] = api_key
        return session, "API key"

    # 2. Login to get JWT + cookies
    username = os.getenv("LANGFLOW_USERNAME", "langflow")
    password = os.getenv("LANGFLOW_PASSWORD", "langflow")
    try:
        login_resp = session.post(
            f"{LANGFLOW_BASE_URL}/api/v1/login",
            data={"username": username, "password": password},
            timeout=10,
        )
        if login_resp.status_code == 200:
            token = login_resp.json().get("access_token")
            if token:
                session.headers["Authorization"] = f"Bearer {token}"
            return session, "JWT login"
    except Exception:
        pass

    # 3. No auth
    return session, "none"


def run_flow(resume_text: str, job_text: str) -> str:
    """Call the Langflow /api/v1/run endpoint and return the output text."""
    url = f"{LANGFLOW_BASE_URL}/api/v1/run/{FLOW_ID}"
    payload = {
        "output_type": "text",
        "input_type": "text",
        "tweaks": {
            RESUME_NODE_ID: {"input_value": resume_text},
            JOB_NODE_ID: {"input_value": job_text},
        },
    }
    session, _ = _get_session()
    resp = session.post(url, json=payload, timeout=120)
    resp.raise_for_status()

    data = resp.json()

    # Extract the final text from Langflow's response structure
    try:
        outputs = data["outputs"]
        # Walk through output list → results → messages
        for output_group in outputs:
            for result in output_group.get("outputs", []):
                msgs = result.get("results", {}).get("message", {})
                text = msgs.get("text", "")
                if text:
                    return text
                # Fallback: check data field
                data_field = msgs.get("data", {})
                if isinstance(data_field, dict) and data_field.get("text"):
                    return data_field["text"]
    except (KeyError, IndexError, TypeError):
        pass

    # Last-resort fallback: dump the raw response for debugging
    return json.dumps(data, indent=2)


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title="ApplyIQ",
        page_icon="🎯",
        layout="wide",
    )

    # ---- Custom CSS ----
    st.markdown(
        """
        <style>
        .block-container { max-width: 1100px; padding-top: 2rem; }
        h1 { margin-bottom: 0.2rem; }
        .subtitle { color: #6b7280; font-size: 1.05rem; margin-bottom: 1.5rem; }
        .result-card {
            background-color: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 1.5rem;
            margin-top: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ---- Sidebar: connection status ----
    with st.sidebar:
        st.caption("Connection")
        st.code(LANGFLOW_BASE_URL, language=None)
        _, auth_label = _get_session()
        if auth_label == "none":
            st.info(f"Auth: {auth_label}")
        else:
            st.success(f"Auth: {auth_label}")

    # ---- Header ----
    st.title("ApplyIQ")
    st.markdown(
        '<p class="subtitle">'
        "Paste your resume and a job description. ApplyIQ will parse both, "
        "research the company, and generate a tailored application package."
        "</p>",
        unsafe_allow_html=True,
    )

    # ---- Input columns ----
    col_resume, col_job = st.columns(2, gap="large")

    with col_resume:
        st.subheader("Resume")
        resume_text = st.text_area(
            "Paste your resume text",
            height=320,
            placeholder="Paste your full resume here …",
            label_visibility="collapsed",
        )

    with col_job:
        st.subheader("Job Description")
        job_text = st.text_area(
            "Paste the job description",
            height=320,
            placeholder="Paste the full job posting here …",
            label_visibility="collapsed",
        )

    # ---- Generate button ----
    run_disabled = not (resume_text.strip() and job_text.strip())

    if st.button("Generate Application Package", type="primary", disabled=run_disabled, use_container_width=True):
        with st.spinner("Running ApplyIQ pipeline — parsing, researching, tailoring …"):
            try:
                result = run_flow(resume_text, job_text)
                st.session_state["result"] = result
            except requests.exceptions.ConnectionError:
                st.error(
                    "Could not connect to the Langflow server. "
                    f"Make sure Langflow is running at **{LANGFLOW_BASE_URL}**."
                )
                return
            except requests.exceptions.HTTPError as exc:
                if exc.response.status_code == 403:
                    st.error(
                        "**403 Forbidden** — Langflow rejected the request. "
                        "Restart Langflow with `LANGFLOW_AUTO_LOGIN=true langflow run` "
                        "or set a valid `LANGFLOW_API_KEY` in your `.env` file."
                    )
                else:
                    st.error(f"Langflow returned an error: {exc.response.status_code} — {exc.response.text[:300]}")
                return
            except Exception as exc:
                st.error(f"Unexpected error: {exc}")
                return

    # ---- Results ----
    if "result" in st.session_state:
        st.divider()
        st.subheader("Application Package")
        st.markdown(st.session_state["result"])

        # Download button
        st.download_button(
            label="Download as text",
            data=st.session_state["result"],
            file_name="applyiq_application_package.txt",
            mime="text/plain",
        )


if __name__ == "__main__":
    main()