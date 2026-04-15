"""
ApplyIQ — AI Job Application Agent
Standalone GUI that connects to a Langflow backend.
"""

import os
import io
import json
import requests
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LANGFLOW_BASE_URL = os.getenv("LANGFLOW_BASE_URL", "http://127.0.0.1:7861")
FLOW_ID = os.getenv("LANGFLOW_FLOW_ID", "9dd9a257-0e88-4397-bd19-1a9b51f1f23d")
RESUME_NODE_ID = "TextInput-t7Cut"
JOB_NODE_ID = "TextInput-UGDxh"


def _pdf_to_text(file_bytes: bytes) -> str:
    import pdfplumber
    parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
    return "\n\n".join(parts)


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
    try:
        for output_group in data["outputs"]:
            for out in output_group.get("outputs", []):
                for val in out.get("results", {}).values():
                    if not isinstance(val, dict):
                        continue
                    t = val.get("data", {}).get("text", "")
                    if isinstance(t, str) and len(t) > 30:
                        return t
                    t = val.get("text", "")
                    if isinstance(t, str) and len(t) > 30:
                        return t
    except Exception:
        pass
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
    st.set_page_config(page_title="ApplyIQ", page_icon="\U0001f3af", layout="wide")
    st.markdown(
        "<style>.block-container{max-width:1100px;padding-top:2rem;}</style>",
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
        "Paste your resume and job description, or upload PDFs. "
        "ApplyIQ will research the company and generate a tailored application package."
    )

    col_resume, col_job = st.columns(2, gap="large")

    with col_resume:
        st.subheader("Resume")
        use_pdf_r = st.checkbox("Upload PDF instead", key="use_pdf_resume")
        if use_pdf_r:
            uploaded_r = st.file_uploader("Resume PDF", type=["pdf"], key="resume_pdf", label_visibility="collapsed")
            if uploaded_r:
                resume_text = _pdf_to_text(uploaded_r.read())
                st.success(f"Extracted {len(resume_text):,} chars from {uploaded_r.name}")
                resume_text = st.text_area("Edit extracted text", value=resume_text, height=250, key="resume_extracted")
            else:
                resume_text = ""
        else:
            resume_text = st.text_area("Resume", height=300, placeholder="Paste your full resume here", label_visibility="collapsed", key="resume_text")

    with col_job:
        st.subheader("Job Description")
        use_pdf_j = st.checkbox("Upload PDF instead", key="use_pdf_job")
        if use_pdf_j:
            uploaded_j = st.file_uploader("Job Description PDF", type=["pdf"], key="job_pdf", label_visibility="collapsed")
            if uploaded_j:
                job_text = _pdf_to_text(uploaded_j.read())
                st.success(f"Extracted {len(job_text):,} chars from {uploaded_j.name}")
                job_text = st.text_area("Edit extracted text", value=job_text, height=250, key="job_extracted")
            else:
                job_text = ""
        else:
            job_text = st.text_area("Job Description", height=300, placeholder="Paste the full job posting here", label_visibility="collapsed", key="job_text")

    run_disabled = not (resume_text.strip() and job_text.strip())
    if st.button("Generate Application Package", type="primary", disabled=run_disabled, use_container_width=True):
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
        st.download_button("Download as text", st.session_state["result"], "applyiq_application_package.txt", "text/plain")


if __name__ == "__main__":
    main()