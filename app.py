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


# ── Theme palettes ─────────────────────────────────────────────────────────────
DARK = dict(
    bg="#0B0B0C", surface="#141418", border="#2A2A2E",
    text_primary="#F5F5F5", text_secondary="#C9C9CE", text_muted="#9A9AA3",
    input_bg="#141418", placeholder="#5A5A65",
    gold="#C9A44C", gold_hover="#A67B23",
    btn_text="#0B0B0C",
    btn_disabled_bg="#1E1E22", btn_disabled_text="#5A5A65",
    tag_bg="#0B0B0C", tag_border="#2A2A2E", tag_text="#9A9AA3",
    toggle_icon="☀️",
    # ghost button for dark mode — no gold
    toggle_bg="transparent", toggle_bg_hover="#1E1E22",
    toggle_border="#2A2A2E", toggle_color="#9A9AA3",
)
LIGHT = dict(
    bg="#FAF8F3", surface="#FFFFFF", border="#E6DDCC",
    text_primary="#1E1A14", text_secondary="#5E5548", text_muted="#8A7E6B",
    input_bg="#FFFDF9", placeholder="#B5A898",
    gold="#B88A2A", gold_hover="#8E6A1F",
    btn_text="#FFFFFF",
    btn_disabled_bg="#EDE8DF", btn_disabled_text="#B5A898",
    tag_bg="#FFFDF9", tag_border="#E6DDCC", tag_text="#8A7E6B",
    toggle_icon="🌙",
    # gold button for light mode
    toggle_bg="#B88A2A", toggle_bg_hover="#8E6A1F",
    toggle_border="#B88A2A", toggle_color="#FFFFFF",
)


def inject_theme(t: dict) -> None:
    st.markdown(f"""
    <style>
    /* ── Kill chrome with display:none — visibility:hidden leaves height ── */
    #MainMenu, footer, header,
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stSidebar"],
    [data-testid="collapsedControl"] {{
        display: none !important;
    }}

    /* ── Page background ── */
    html, body, .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    [data-testid="stMainBlockContainer"] {{
        background-color: {t['bg']} !important;
    }}
    .block-container {{
        max-width: 860px !important;
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
        padding-left: 2.5rem !important;
        padding-right: 2.5rem !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}

    /* ── Steps ── */
    .steps {{
        display: flex; align-items: center;
        margin: 0.5rem 0 1.6rem 0;
        font-size: 0.82rem; color: {t['text_secondary']};
    }}
    .step {{ display: flex; align-items: center; gap: 0.4rem; }}
    .step-num {{
        background: {t['surface']}; color: {t['text_secondary']};
        border: 1px solid {t['border']};
        border-radius: 50%; width: 20px; height: 20px;
        display: inline-flex; align-items: center; justify-content: center;
        font-size: 0.72rem; font-weight: 600; flex-shrink: 0;
    }}
    .step-arrow {{ margin: 0 0.6rem; color: {t['border']}; }}

    /* ── Labels ── */
    .input-label {{
        font-size: 0.72rem; font-weight: 600;
        letter-spacing: 0.09em; text-transform: uppercase;
        color: {t['text_muted']}; margin-bottom: 0.4rem;
    }}

    /* ── Textareas ── */
    .stTextArea textarea {{
        background: {t['input_bg']} !important;
        border: 1px solid {t['border']} !important;
        border-radius: 10px !important;
        color: {t['text_primary']} !important;
        font-size: 0.9rem !important;
    }}
    .stTextArea textarea::placeholder {{ color: {t['placeholder']} !important; }}
    .stTextArea textarea:focus {{
        border-color: {t['gold']} !important;
        box-shadow: 0 0 0 2px rgba(201,164,76,0.15) !important;
    }}

    /* ── Checkbox ── */
    .stCheckbox label p {{ color: {t['text_muted']} !important; font-size: 0.85rem !important; }}

    /* ── Primary CTA — gold, full width ── */
    div[data-testid="stButton"] > button[kind="primary"] {{
        background: {t['gold']} !important;
        color: {t['btn_text']} !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.7rem 1.5rem !important;
        font-size: 1rem !important;
        font-weight: 700 !important;
        width: 100% !important;
    }}
    div[data-testid="stButton"] > button[kind="primary"]:hover:not(:disabled) {{
        background: {t['gold_hover']} !important;
    }}
    div[data-testid="stButton"] > button[kind="primary"]:disabled {{
        background: {t['btn_disabled_bg']} !important;
        color: {t['btn_disabled_text']} !important;
        border: 1px solid {t['border']} !important;
        opacity: 1 !important;
    }}

    /* ── Secondary/toggle — ghost, auto width ── */
    div[data-testid="stButton"] > button[kind="secondary"] {{
        background: {t['toggle_bg']} !important;
        color: {t['toggle_color']} !important;
        border: 1px solid {t['toggle_border']} !important;
        border-radius: 8px !important;
        padding: 0.25rem 0.6rem !important;
        font-size: 1rem !important;
        font-weight: 400 !important;
        width: auto !important;
        min-width: unset !important;
        float: right !important;
    }}
    div[data-testid="stButton"] > button[kind="secondary"]:hover {{
        background: {t['toggle_bg_hover']} !important;
    }}

    /* ── Status pill ── */
    .status-pill {{
        display: inline-flex; align-items: center; gap: 0.3rem;
        border: 1px solid {t['border']}; border-radius: 999px;
        padding: 0.16rem 0.55rem; font-size: 0.68rem; color: {t['text_muted']};
    }}
    .pill-dot {{ width: 6px; height: 6px; border-radius: 50%; }}

    /* ── Result placeholder ── */
    .result-placeholder {{
        border: 1px dashed {t['border']}; border-radius: 10px;
        padding: 1rem 1.75rem; margin-top: 1.5rem;
        display: flex; align-items: center; gap: 1.5rem;
    }}
    .rp-label {{
        font-size: 0.68rem; font-weight: 600; letter-spacing: 0.08em;
        text-transform: uppercase; color: {t['text_muted']}; white-space: nowrap;
    }}
    .rp-tags {{ display: flex; flex-wrap: wrap; gap: 0.4rem; }}
    .rp-tag {{
        background: {t['tag_bg']}; border: 1px solid {t['tag_border']};
        border-radius: 6px; padding: 0.2rem 0.55rem;
        font-size: 0.72rem; color: {t['tag_text']};
    }}

    /* ── Divider ── */
    hr {{ border-color: {t['border']} !important; }}
    </style>
    """, unsafe_allow_html=True)


def main():
    st.set_page_config(page_title="ApplyIQ", page_icon="\U0001f3af", layout="centered")

    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = True

    t = DARK if st.session_state.dark_mode else LIGHT
    inject_theme(t)

    _, auth_label = _get_session()
    dot_color = "#3FAE6A" if auth_label != "none" else "#D45C5C"
    pill_text = "Connected" if auth_label != "none" else "Offline"

    # ── Top bar ───────────────────────────────────────────────────────────────
    pill_col, toggle_col = st.columns([8, 1])
    with pill_col:
        st.markdown(
            f'<div style="padding-top:0.15rem;">'
            f'<span class="status-pill">'
            f'<span class="pill-dot" style="background:{dot_color}"></span>'
            f'{pill_text}</span></div>',
            unsafe_allow_html=True,
        )
    with toggle_col:
        if st.button(t["toggle_icon"], key="theme_toggle"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

    # ── Header + steps ────────────────────────────────────────────────────────
    st.markdown(f"""
    <h1 style="margin-bottom:0.2rem;color:{t['text_primary']};">ApplyIQ</h1>
    <p style="color:{t['text_secondary']};font-size:1rem;margin-top:0;margin-bottom:1.2rem;">
        Analyzes your fit, researches the company, and generates tailored application materials.
    </p>
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

    # ── Amber hint ────────────────────────────────────────────────────────────
    if resume_text.strip() and not job_text.strip():
        st.markdown(
            "<p style='font-size:0.78rem;color:#C98A1A;margin:0.3rem 0;'>"
            "⚠ Add a job description to continue.</p>",
            unsafe_allow_html=True,
        )
    elif job_text.strip() and not resume_text.strip():
        st.markdown(
            "<p style='font-size:0.78rem;color:#C98A1A;margin:0.3rem 0;'>"
            "⚠ Add your resume to continue.</p>",
            unsafe_allow_html=True,
        )

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
            f"<p style='color:{t['text_muted']};font-size:0.85rem;"
            "margin-top:-0.5rem;margin-bottom:1rem;'>"
            "Match summary · Resume bullets · Company insights · Application-ready content"
            "</p>",
            unsafe_allow_html=True,
        )
        st.markdown(st.session_state["result"])
        st.download_button(
            "⬇ Download package",
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


if __name__ == "__main__":
    main()