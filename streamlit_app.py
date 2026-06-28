"""
IT Support Agent — Streamlit UI
================================
Run with:
    streamlit run streamlit_app.py

Requires it_support_agent.py to be in the same directory.
"""

import uuid
import streamlit as st
from langgraph.types import Command

# Import everything from the core agent module
from it_support_agent import build_workflow, find_cached_resolution

# ──────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="IT Support Agent",
    page_icon="🎫",
    layout="centered",
)

# ──────────────────────────────────────────────
# Custom CSS
# ──────────────────────────────────────────────

st.markdown("""
<style>
  /* Page background */
  [data-testid="stAppViewContainer"] {
    background: #f4f6fb;
  }

  /* Hide default Streamlit header */
  [data-testid="stHeader"] { background: transparent; }

  /* Top banner */
  .banner {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border-radius: 14px;
    padding: 28px 32px 22px;
    margin-bottom: 28px;
    color: white;
  }
  .banner h1 { margin: 0; font-size: 1.8rem; }
  .banner p  { margin: 6px 0 0; color: #aab4cc; font-size: 0.95rem; }

  /* Cards */
  .card {
    background: white;
    border-radius: 12px;
    padding: 22px 26px;
    margin-bottom: 18px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
  }
  .card h3 { margin: 0 0 14px; font-size: 1rem; color: #1a1a2e; }

  /* Step badges */
  .step-badge {
    display: inline-block;
    background: #e8ecf8;
    color: #1a1a2e;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.78rem;
    font-weight: 600;
    margin-bottom: 10px;
  }

  /* Priority badges */
  .badge-LOW      { background:#d4edda; color:#155724; border-radius:8px; padding:3px 10px; font-weight:600; font-size:0.82rem; }
  .badge-MEDIUM   { background:#fff3cd; color:#856404; border-radius:8px; padding:3px 10px; font-weight:600; font-size:0.82rem; }
  .badge-HIGH     { background:#ffe5d0; color:#7c3500; border-radius:8px; padding:3px 10px; font-weight:600; font-size:0.82rem; }
  .badge-CRITICAL { background:#f8d7da; color:#721c24; border-radius:8px; padding:3px 10px; font-weight:600; font-size:0.82rem; }

  /* Resolution step list */
  .step-item {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 10px 0;
    border-bottom: 1px solid #f0f0f0;
  }
  .step-num {
    background: #1a1a2e;
    color: white;
    border-radius: 50%;
    width: 26px; height: 26px;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.78rem; font-weight: 700;
    flex-shrink: 0;
  }
  .step-text { font-size: 0.93rem; line-height: 1.5; padding-top: 3px; }

  /* Ticket info rows */
  .ticket-row {
    display: flex;
    padding: 9px 0;
    border-bottom: 1px solid #f4f4f4;
    font-size: 0.92rem;
  }
  .ticket-label { color: #666; width: 150px; flex-shrink: 0; font-weight: 500; }
  .ticket-value { color: #1a1a2e; }

  /* Status pill */
  .pill-success { background:#d4edda; color:#155724; border-radius:20px; padding:3px 12px; font-size:0.82rem; font-weight:600; }
  .pill-warn    { background:#fff3cd; color:#856404; border-radius:20px; padding:3px 12px; font-size:0.82rem; font-weight:600; }
  .pill-cached  { background:#e0e7ff; color:#3730a3; border-radius:20px; padding:3px 12px; font-size:0.82rem; font-weight:600; }

  /* Analysis grid */
  .analysis-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-top: 4px;
  }
  .analysis-item { background:#f9fafc; border-radius:8px; padding:10px 14px; }
  .analysis-item .label { font-size:0.75rem; color:#888; text-transform:uppercase; letter-spacing:0.5px; }
  .analysis-item .value { font-size:0.92rem; color:#1a1a2e; font-weight:500; margin-top:2px; }

  /* Info box */
  .info-box {
    background: #f0f4ff;
    border-left: 4px solid #4f6ef7;
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    font-size: 0.9rem;
    color: #2d3a6b;
    margin-bottom: 14px;
  }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Session state initialisation
# ──────────────────────────────────────────────

def init_session():
    defaults = {
        "workflow":        None,
        "stage":           "form",        # form | processing | clarify | result
        "thread_id":       None,
        "last_result":     None,
        "questions":       [],
        "user_name":       "",
        "user_email":      "",
        "user_issue":      "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

# Build the workflow once and cache it
if st.session_state.workflow is None:
    with st.spinner("Initialising agent…"):
        st.session_state.workflow = build_workflow()

# ──────────────────────────────────────────────
# Helper renderers
# ──────────────────────────────────────────────

def render_banner():
    st.markdown("""
    <div class="banner">
      <h1>🎫 IT Support Agent</h1>
      <p>Describe your issue and we'll resolve it instantly — or raise a ticket for the admin team.</p>
    </div>
    """, unsafe_allow_html=True)


def render_analysis(result: dict):
    severity = result.get("severity", "N/A")
    badge_cls = f"badge-{severity}" if severity in ("LOW","MEDIUM","HIGH","CRITICAL") else "badge-MEDIUM"
    st.markdown(f"""
    <div class="card">
      <span class="step-badge">🔍 Issue Analysis</span>
      <div class="analysis-grid">
        <div class="analysis-item">
          <div class="label">Category</div>
          <div class="value">{result.get("issue_category", "N/A")}</div>
        </div>
        <div class="analysis-item">
          <div class="label">Affected System</div>
          <div class="value">{result.get("affected_system", "N/A")}</div>
        </div>
        <div class="analysis-item">
          <div class="label">Severity</div>
          <div class="value"><span class="{badge_cls}">{severity}</span></div>
        </div>
        <div class="analysis-item">
          <div class="label">Confidence</div>
          <div class="value">{int(float(result.get("confidence", 0)) * 100)}%</div>
        </div>
      </div>
      <div style="margin-top:12px; background:#f9fafc; border-radius:8px; padding:10px 14px;">
        <div style="font-size:0.75rem; color:#888; text-transform:uppercase; letter-spacing:0.5px;">Summary</div>
        <div style="font-size:0.92rem; color:#1a1a2e; margin-top:3px;">{result.get("issue_summary", "N/A")}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_resolution(result: dict):
    steps   = result.get("solution_step", [])
    cached  = result.get("knowledge_cache_hit", False)
    source_pill = '<span class="pill-cached">⚡ From knowledge base</span>' if cached else '<span class="pill-success">🤖 Generated by AI</span>'
    eta     = result.get("estimation_resolution_time", "")
    eta_html = f'<span style="color:#888;font-size:0.85rem;"> · ⏱ {eta}</span>' if eta else ""

    steps_html = "".join(
        f'<div class="step-item"><div class="step-num">{i+1}</div><div class="step-text">{s}</div></div>'
        for i, s in enumerate(steps)
    )

    st.markdown(f"""
    <div class="card">
      <span class="step-badge">✅ Resolution</span>
      <div style="display:flex; align-items:center; gap:8px; margin-bottom:14px;">
        {source_pill}{eta_html}
      </div>
      {steps_html}
    </div>
    """, unsafe_allow_html=True)


def render_ticket(result: dict):
    priority  = result.get("ticket_priority", "N/A")
    badge_cls = f"badge-{priority}" if priority in ("LOW","MEDIUM","HIGH","CRITICAL") else "badge-MEDIUM"
    email_ok  = result.get("ticket_email_sent", False)
    email_pill = '<span class="pill-success">✅ Email sent to admin</span>' if email_ok else '<span class="pill-warn">⚠️ Email not sent — check SMTP config</span>'

    st.markdown(f"""
    <div class="card">
      <span class="step-badge">🎫 Support Ticket Raised</span>
      <div class="ticket-row"><span class="ticket-label">Ticket ID</span>    <span class="ticket-value"><strong>{result.get("ticket_id","N/A")}</strong></span></div>
      <div class="ticket-row"><span class="ticket-label">Title</span>        <span class="ticket-value">{result.get("ticket_title","N/A")}</span></div>
      <div class="ticket-row"><span class="ticket-label">Priority</span>     <span class="ticket-value"><span class="{badge_cls}">{priority}</span></span></div>
      <div class="ticket-row"><span class="ticket-label">Category</span>     <span class="ticket-value">{result.get("ticket_category","N/A")}</span></div>
      <div class="ticket-row"><span class="ticket-label">Status</span>       <span class="ticket-value">{result.get("ticket_status","OPEN")}</span></div>
      <div class="ticket-row" style="border:none;">
        <span class="ticket-label">Notification</span>
        <span class="ticket-value">{email_pill}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if email_ok and result.get("user_email"):
        st.markdown(f"""
        <div class="info-box">
          📧 A copy of this ticket has also been sent to <strong>{result.get("user_email")}</strong>
        </div>
        """, unsafe_allow_html=True)


def reset():
    for k in ["stage", "thread_id", "last_result", "questions", "user_name", "user_email", "user_issue"]:
        if k == "stage":
            st.session_state[k] = "form"
        elif k in ("questions",):
            st.session_state[k] = []
        else:
            st.session_state[k] = ""
    st.session_state.last_result = None

# ──────────────────────────────────────────────
# Stage: FORM
# ──────────────────────────────────────────────

def stage_form():
    render_banner()

    st.markdown('<div class="card"><span class="step-badge">Step 1 — Tell us about yourself</span>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Your Name", placeholder="e.g. Rahul Sharma", key="input_name")
    with col2:
        email = st.text_input("Your Email", placeholder="e.g. rahul@company.com", key="input_email")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><span class="step-badge">Step 2 — Describe your issue</span>', unsafe_allow_html=True)
    issue = st.text_area(
        "What's the problem?",
        placeholder="e.g. I cannot connect to the VPN. It shows 'Authentication failed' every time I try.",
        height=130,
        key="input_issue",
    )
    st.markdown('</div>', unsafe_allow_html=True)

    submitted = st.button("🚀 Submit Issue", use_container_width=True, type="primary")

    if submitted:
        errors = []
        if not name.strip():
            errors.append("Please enter your name.")
        if not email.strip() or "@" not in email:
            errors.append("Please enter a valid email address.")
        if not issue.strip():
            errors.append("Please describe your issue.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            st.session_state.user_name  = name.strip()
            st.session_state.user_email = email.strip()
            st.session_state.user_issue = issue.strip()
            st.session_state.thread_id  = str(uuid.uuid4())
            st.session_state.stage      = "processing"
            st.rerun()

# ──────────────────────────────────────────────
# Stage: PROCESSING
# ──────────────────────────────────────────────

def stage_processing():
    render_banner()

    st.markdown(f"""
    <div class="info-box">
      Analysing issue for <strong>{st.session_state.user_name}</strong>…
    </div>
    """, unsafe_allow_html=True)

    config = {"configurable": {"thread_id": st.session_state.thread_id}}

    initial_state = {
        "user_name":            st.session_state.user_name,
        "user_email":           st.session_state.user_email,
        "user_issue":           st.session_state.user_issue,
        "clarification_answer": [],
        "classification_count": 0,
    }

    with st.spinner("Working on it…"):
        result = st.session_state.workflow.invoke(initial_state, config=config)

    if "__interrupt__" in result:
        st.session_state.questions   = result["__interrupt__"][0].value["questions"]
        st.session_state.last_result = result
        st.session_state.stage       = "clarify"
    else:
        st.session_state.last_result = result
        st.session_state.stage       = "result"

    st.rerun()

# ──────────────────────────────────────────────
# Stage: CLARIFY  (HITL questions)
# ──────────────────────────────────────────────

def stage_clarify():
    render_banner()

    st.markdown("""
    <div class="card">
      <span class="step-badge">🤖 A few more details needed</span>
      <p style="color:#555; font-size:0.93rem; margin:0 0 16px;">
        To help resolve your issue, please answer the questions below.
      </p>
    </div>
    """, unsafe_allow_html=True)

    questions = st.session_state.questions
    answers   = []

    with st.form("clarify_form"):
        for i, q in enumerate(questions):
            ans = st.text_input(f"Q{i+1}. {q}", key=f"clarify_{i}")
            answers.append(ans)
        submitted = st.form_submit_button("Submit Answers", use_container_width=True, type="primary")

    if submitted:
        if any(not a.strip() for a in answers):
            st.warning("Please answer all questions before submitting.")
        else:
            config = {"configurable": {"thread_id": st.session_state.thread_id}}
            with st.spinner("Resuming analysis…"):
                result = st.session_state.workflow.invoke(
                    Command(resume=[a.strip() for a in answers]),
                    config=config,
                )

            if "__interrupt__" in result:
                st.session_state.questions   = result["__interrupt__"][0].value["questions"]
                st.session_state.last_result = result
                st.rerun()
            else:
                st.session_state.last_result = result
                st.session_state.stage       = "result"
                st.rerun()

# ──────────────────────────────────────────────
# Stage: RESULT
# ──────────────────────────────────────────────

def stage_result():
    render_banner()

    result = st.session_state.last_result

    # User recap
    st.markdown(f"""
    <div class="card">
      <span class="step-badge">👤 Submitted by</span>
      <div style="display:flex; gap:24px; flex-wrap:wrap; margin-top:4px;">
        <div><span style="color:#888;font-size:0.85rem;">Name</span><br><strong>{result.get("user_name","N/A")}</strong></div>
        <div><span style="color:#888;font-size:0.85rem;">Email</span><br><strong>{result.get("user_email","N/A")}</strong></div>
      </div>
      <div style="margin-top:12px; background:#f9fafc; border-radius:8px; padding:10px 14px;">
        <div style="font-size:0.75rem; color:#888; text-transform:uppercase; letter-spacing:0.5px;">Issue</div>
        <div style="font-size:0.92rem; color:#1a1a2e; margin-top:3px;">{result.get("user_issue","N/A")}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Analysis card
    render_analysis(result)

    # Resolution or ticket
    decision = result.get("decision", "")
    if decision == "USER_SOLVABLE":
        render_resolution(result)
    else:
        render_ticket(result)

    # Clarification Q&A (if any)
    questions = result.get("clarification_questions") or []
    answers   = result.get("clarification_answer") or []
    if questions:
        qa_html = "".join(
            f"""
            <div class="ticket-row">
              <span class="ticket-label" style="width:auto;min-width:0;flex:1;">
                <strong>Q{i+1}:</strong> {q}
              </span>
            </div>
            <div class="ticket-row" style="padding-left:16px; color:#555;">
              → {answers[i] if i < len(answers) else "—"}
            </div>
            """
            for i, q in enumerate(questions)
        )
        st.markdown(f"""
        <div class="card">
          <span class="step-badge">🗣️ Clarification Provided</span>
          {qa_html}
        </div>
        """, unsafe_allow_html=True)

    # New issue button
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Submit Another Issue", use_container_width=True):
        reset()
        st.rerun()

# ──────────────────────────────────────────────
# Router
# ──────────────────────────────────────────────

stage = st.session_state.stage

if stage == "form":
    stage_form()
elif stage == "processing":
    stage_processing()
elif stage == "clarify":
    stage_clarify()
elif stage == "result":
    stage_result()