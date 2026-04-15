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
    st.set_page_config(page_title="ApplyIQ", page_icon="\U0001f3af", layout="centered")

    # ── Global styles ──────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    /* Hide Streamlit default chrome */
    #MainMenu, footer, header { visibility: hidden; }

    /* Page background */
    .stApp { background-color: #0f1117; }

    /* Widen the centered layout and reduce top padding */
    .block-container {
        max-width: 900px !important;
        padding-top: 1.5rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }

    /* Main card — more contrast/elevation */
    .main-card {
        background: #1c1f2e;
        border: 1px solid #363a56;
        border-radius: 16px;
        padding: 2.2rem 2.5rem 2rem 2.5rem;
        margin: 0 auto;
        box-shadow: 0 4px 32px rgba(0,0,0,0.35);
    }

    /* Steps bar */
    .steps {
        display: flex;
        gap: 0;
        margin: 1rem 0 1.8rem 0;
        font-size: 0.82rem;
        color: #b0b8d0;
    }
    .step {
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    .step-num {
        background: #363a56;
        color: #d4d8f0;
        border-radius: 50%;
        width: 20px;
        height: 20px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 0.72rem;
        font-weight: 600;
        flex-shrink: 0;
    }
    .step-arrow {
        margin: 0 0.6rem;
        color: #4a5068;
    }

    /* Section labels */
    .input-label {
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #b0b8d0;
        margin-bottom: 0.5rem;
    }

    /* Textarea polish */
    .stTextArea textarea {
        border: 1px solid #3a3f5c !important;
        border-radius: 10px !important;
        background: #14172030 !important;
    }
    .stTextArea textarea:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 2px rgba(99,102,241,0.15) !important;
    }

    /* CTA button */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.75rem 1.5rem !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.01em !important;
        transition: opacity 0.15s !important;
    }
    .stButton > button[kind="primary"]:hover { opacity: 0.88 !important; }
    .stButton > button[kind="primary"]:disabled {
        background: linear-gradient(135deg, #3d3f6e 0%, #2e3060 100%) !important;
        color: #8b8fb8 !important;
        opacity: 1 !important;
        cursor: not-allowed !important;
    }

    /* Result preview placeholder — product-like list */
    .result-placeholder {
        border: 1px dashed #363a56;
        border-radius: 10px;
        padding: 1.1rem 2rem;
        margin-top: 1.5rem;
        display: flex;
        align-items: center;
        gap: 2rem;
    }
    .rp-label {
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.07em;
        text-transform: uppercase;
        color: #6b7280;
        white-space: nowrap;
    }
    .rp-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
    }
    .rp-tag {
        background: #1e2238;
        border: 1px solid #2e3147;
        border-radius: 6px;
        padding: 0.25rem 0.65rem;
        font-size: 0.75rem;
        color: #6b7280;
    }

    /* Status pill — smaller, less dominant */
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        background: transparent;
        border: 1px solid #2a2d40;
        border-radius: 999px;
        padding: 0.18rem 0.6rem;
        font-size: 0.7rem;
        color: #6b7280;
        margin-bottom: 1.2rem;
    }
    .pill-dot { width: 6px; height: 6px; border-radius: 50%; background: #22c55e; }

    /* Sidebar hidden by default on load */
    [data-testid="stSidebar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

    # ── Hidden sidebar (connection debug) ─────────────────────────────────────
    with st.sidebar:
        st.caption("Connection debug")
        st.code(LANGFLOW_BASE_URL, language=None)
        _, auth_label = _get_session()
        if auth_label == "none":
            st.warning(f"Auth: {auth_label}")
        else:
            st.success(f"Auth: {auth_label}")

    # ── Status pill ───────────────────────────────────────────────────────────
    _, auth_label = _get_session()
    dot_color = "#22c55e" if auth_label != "none" else "#ef4444"
    pill_text = "Connected" if auth_label != "none" else "Offline"
    st.markdown(
        f'<div class="status-pill">'
        f'<span class="pill-dot" style="background:{dot_color}"></span>'
        f'{pill_text}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("# ApplyIQ")
    st.markdown(
        "<p style='color:#b0b8d0;font-size:1.05rem;margin-top:-0.4rem;margin-bottom:1.2rem;'>"
        "Analyzes your fit, researches the company, and generates tailored application materials."
        "</p>",
        unsafe_allow_html=True,
    )

    # ── 3-step workflow cue ───────────────────────────────────────────────────
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown("""
    <div class="steps">
        <div class="step"><span class="step-num">1</span> Add materials</div>
        <span class="step-arrow">›</span>
        <div class="step"><span class="step-num">2</span> Analyze fit</div>
        <span class="step-arrow">›</span>
        <div class="step"><span class="step-num">3</span> Generate package</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Inputs ────────────────────────────────────────────────────────────────
    col_resume, col_job = st.columns(2, gap="large")

    with col_resume:
        st.markdown('<div class="input-label">Resume</div>', unsafe_allow_html=True)
        use_pdf_r = st.checkbox("Upload PDF", key="use_pdf_resume")
        if use_pdf_r:
            uploaded_r = st.file_uploader(
                "Resume PDF", type=["pdf"], key="resume_pdf",
                label_visibility="collapsed"
            )
            if uploaded_r:
                resume_text = _pdf_to_text(uploaded_r.read())
                st.success(f"{len(resume_text):,} chars extracted")
                resume_text = st.text_area(
                    "Edit if needed", value=resume_text,
                    height=220, key="resume_extracted"
                )
            else:
                resume_text = ""
        else:
            resume_text = st.text_area(
                "Resume", height=280,
                placeholder="Paste your full resume here",
                label_visibility="collapsed", key="resume_text"
            )

    with col_job:
        st.markdown('<div class="input-label">Job Description</div>', unsafe_allow_html=True)
        use_pdf_j = st.checkbox("Upload PDF", key="use_pdf_job")
        if use_pdf_j:
            uploaded_j = st.file_uploader(
                "Job PDF", type=["pdf"], key="job_pdf",
                label_visibility="collapsed"
            )
            if uploaded_j:
                job_text = _pdf_to_text(uploaded_j.read())
                st.success(f"{len(job_text):,} chars extracted")
                job_text = st.text_area(
                    "Edit if needed", value=job_text,
                    height=220, key="job_extracted"
                )
            else:
                job_text = ""
        else:
            job_text = st.text_area(
                "Job Description", height=280,
                placeholder="Paste the full job posting here",
                label_visibility="collapsed", key="job_text"
            )

    st.markdown("<div style='margin-top:0.5rem'></div>", unsafe_allow_html=True)

    # ── CTA ───────────────────────────────────────────────────────────────────
    run_disabled = not (resume_text.strip() and job_text.strip())
    if st.button(
        "Generate Package",
        type="primary",
        disabled=run_disabled,
        use_container_width=True,
    ):
        with st.spinner("Analyzing fit, researching company, generating package..."):
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

    # ── Result or placeholder ─────────────────────────────────────────────────
    if "result" in st.session_state:
        st.divider()
        st.subheader("Your Application Package")
        st.markdown(
            "<p style='color:#6b7280;font-size:0.85rem;margin-top:-0.5rem;margin-bottom:1rem;'>"
            "Match summary · Resume bullets · Company insights · Application-ready content"
            "</p>",
            unsafe_allow_html=True,
        )
        st.markdown(st.session_state["result"])
        st.download_button(
            "Download as text",
            st.session_state["result"],
            "applyiq_application_package.txt",
            "text/plain",
        )
    else:
        st.markdown("""
        <div class="result-placeholder">
            <span class="rp-label">Output</span>
            <div class="rp-tags">
                <span class="rp-tag">Match summary</span>
                <span class="rp-tag">Resume bullet suggestions</span>
                <span class="rp-tag">Cover letter draft</span>
                <span class="rp-tag">Company insights</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # close .main-card


if __name__ == "__main__":
    main()