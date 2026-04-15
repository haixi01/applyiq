"""
ApplyIQ — AI Job Application Agent
Standalone GUI that connects to a Langflow backend.
"""

import os
import json
import requests
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LANGFLOW_BASE_URL = os.getenv("LANGFLOW_BASE_URL", "http://127.0.0.1:7860")
FLOW_ID = os.getenv("LANGFLOW_FLOW_ID", "9dd9a257-0e88-4397-bd19-1a9b51f1f23d")
RESUME_NODE_ID = "TextInput-t7Cut"
JOB_NODE_ID = "TextInput-UGDxh"


def _get_session():
    session = requests.Session()
    api_key = os.getenv("LANGFLOW_API_KEY")
    if api_key:
        session.headers["x-api-key"] = api_key
        return session, "API key"
    username = os.getenv("LANGFLOW_USERNAME", "langflow")
    password = os.getenv("LANGFLOW_PASSWORD", "langflow")
    try:
        r = session.post(
            f"{LANGFLOW_BASE_URL}/api/v1/login",
            data={"username": username, "password": password},
            timeout=10,
        )
        if r.status_code == 200:
            token = r.json().get("access_token")
            if token:
                session.headers["Authorization"] = f"Bearer {token}"
            return session, "JWT login"
    except Exception:
        pass
    return session, "none"


def _extract_text(data: dict) -> str:
    """Navigate the known Langflow response structure to get the output text."""
    try:
        for output_group in data["outputs"]:
            for out in output_group.get("outputs", []):
                results = out.get("results", {})
                for val in results.values():
                    if not isinstance(val, dict):
                        continue
                    # Path 1: results -> message -> data -> text
                    t = val.get("data", {}).get("text", "")
                    if isinstance(t, str) and len(t) > 30:
                        return t
                    # Path 2: results -> message -> text
                    t = val.get("text", "")
                    if isinstance(t, str) and len(t) > 30:
                        return t
    except Exception:
        pass
    # Last resort: return raw JSON so at least something shows
    return json.dumps(data, indent=2)


def run_flow(resume_text: str, job_text: str) -> str:
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
    resp = session.post(url, json=payload, timeout=180)
    resp.raise_for_status()
    return _extract_text(resp.json())


def main():
    st.set_page_config(page_title="ApplyIQ", page_icon="🎯", layout="wide")

    st.markdown(
        """
        <style>
        .block-container { max-width: 1100px; padding-top: 2rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.caption("Connection")
        st.code(LANGFLOW_BASE_URL, language=None)
        _, auth_label = _get_session()
        if auth_label == "none":
            st.info(f"Auth: {auth_label}")
        else:
            st.success(f"Auth: {auth_label}")

    st.title("ApplyIQ")
    st.markdown(
        "Paste your resume and a job description. "
        "ApplyIQ will parse both, research the company, "
        "and generate a tailored application package."
    )

    col_resume, col_job = st.columns(2, gap="large")
    with col_resume:
        st.subheader("Resume")
        resume_text = st.text_area(
            "Resume", height=320,
            placeholder="Paste your full resume here",
            label_visibility="collapsed",
        )
    with col_job:
        st.subheader("Job Description")
        job_text = st.text_area(
            "Job Description", height=320,
            placeholder="Paste the full job posting here",
            label_visibility="collapsed",
        )

    run_disabled = not (resume_text.strip() and job_text.strip())
    if st.button("Generate Application Package", type="primary",
                 disabled=run_disabled, use_container_width=True):
        with st.spinner("Running ApplyIQ pipeline — parsing, researching, tailoring..."):
            try:
                result = run_flow(resume_text, job_text)
                st.session_state["result"] = result
            except requests.exceptions.ConnectionError:
                st.error(f"Could not connect to Langflow at **{LANGFLOW_BASE_URL}**.")
                return
            except requests.exceptions.HTTPError as exc:
                st.error(f"Langflow error: {exc.response.status_code} — {exc.response.text[:300]}")
                return
            except Exception as exc:
                st.error(f"Unexpected error: {exc}")
                return

    if "result" in st.session_state:
        st.divider()
        st.subheader("Application Package")
        st.markdown(st.session_state["result"])
        st.download_button(
            label="Download as text",
            data=st.session_state["result"],
            file_name="applyiq_application_package.txt",
            mime="text/plain",
        )


if __name__ == "__main__":
    main()