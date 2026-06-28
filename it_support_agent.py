"""
IT Support Agent
================
A LangGraph-based IT support agent that:
  1. Checks knowledge.json for a cached resolution before calling the LLM
  2. Analyses the user's issue
  3. Classifies it (USER_SOLVABLE / ADMIN_REQUIRED / NEED_MORE_INFO)
  4. Asks clarifying questions when needed (human-in-the-loop)
  5. Generates a resolution or raises a support ticket
  6. Saves every USER_SOLVABLE resolution to knowledge.json for future reuse
  7. Emails the ticket to the admin team via SMTP for ADMIN_REQUIRED issues
  8. Prints a final report
  
Requirements:
    pip install langgraph langchain-openai python-dotenv pydantic
"""

import json
import os
import smtplib
import uuid
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Literal

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

load_dotenv()

# ──────────────────────────────────────────────
# Knowledge Base  (knowledge.json)
# ──────────────────────────────────────────────

KNOWLEDGE_FILE = Path("knowledge.json")


def _load_knowledge() -> list:
    """Return the full list of knowledge entries, or [] if file is missing/empty."""
    if not KNOWLEDGE_FILE.exists():
        return []
    try:
        data = json.loads(KNOWLEDGE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_knowledge(entries: list) -> None:
    """Write the full list back to knowledge.json (pretty-printed)."""
    KNOWLEDGE_FILE.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def find_cached_resolution(issue_category: str, affected_system: str) -> dict | None:
    """
    Look for an existing resolution that matches on both category and system.
    Returns the entry dict, or None if nothing found.
    Matching is case-insensitive.
    """
    entries = _load_knowledge()
    cat  = issue_category.lower().strip()
    sys_ = affected_system.lower().strip()

    for entry in entries:
        if (
            entry.get("issue_category", "").lower().strip() == cat
            and entry.get("affected_system", "").lower().strip() == sys_
        ):
            return entry
    return None


def append_to_knowledge(state: dict) -> None:
    """
    Append a new USER_SOLVABLE resolution to knowledge.json.
    Skips saving if the same category + system already exists.
    """
    existing = find_cached_resolution(
        state.get("issue_category", ""),
        state.get("affected_system", ""),
    )
    if existing:
        return

    entries = _load_knowledge()
    entries.append(
        {
            "issue_category":             state.get("issue_category", ""),
            "affected_system":            state.get("affected_system", ""),
            "issue_summary":              state.get("issue_summary", ""),
            "solution_step":              state.get("solution_step", []),
            "knowledge_source":           state.get("knowledge_source", ""),
            "estimation_resolution_time": state.get("estimation_resolution_time", ""),
            "saved_at":                   datetime.now().isoformat(timespec="seconds"),
        }
    )
    _save_knowledge(entries)
    print(f"📚 Saved to knowledge.json  [{state.get('issue_category')} / {state.get('affected_system')}]")


# ──────────────────────────────────────────────
# Email  (SMTP ticket notification)
# ──────────────────────────────────────────────

def _build_ticket_email(state: dict) -> tuple[str, str]:
    """
    Return (subject, html_body) for the admin ticket email.
    Contains full context: ticket info, user details, issue description,
    affected system, severity, business impact, and clarification Q&A.
    """
    ticket_id = state.get("ticket_id", f"TKT-{uuid.uuid4().hex[:8].upper()}")

    priority_color = {
        "LOW":      "#28a745",
        "MEDIUM":   "#ffc107",
        "HIGH":     "#fd7e14",
        "CRITICAL": "#dc3545",
    }.get(state.get("ticket_priority", "MEDIUM"), "#6c757d")

    subject = (
        f"[{state.get('ticket_priority', 'N/A')}] "
        f"New Support Ticket #{ticket_id} — {state.get('ticket_title', 'N/A')}"
    )

    # Build clarification Q&A block only if questions were asked
    clarification_html = ""
    questions = state.get("clarification_questions") or []
    answers   = state.get("clarification_answer") or []
    if questions:
        qa_rows = "".join(
            f"""
            <tr style="{'background:#f9f9f9;' if i % 2 == 0 else ''}">
              <td style="padding:8px 10px; color:#555; vertical-align:top; width:40%;">
                <strong>Q{i+1}:</strong> {q}
              </td>
              <td style="padding:8px 10px; vertical-align:top;">
                {answers[i] if i < len(answers) else "<em>No answer provided</em>"}
              </td>
            </tr>"""
            for i, q in enumerate(questions)
        )
        clarification_html = f"""
    <h3 style="color:#1a1a2e; margin:24px 0 10px;">🗣️ Clarification Details</h3>
    <table style="width:100%; border-collapse:collapse; border:1px solid #eee; border-radius:6px;">
      {qa_rows}
    </table>"""

    def row(label: str, value: str, shaded: bool = False) -> str:
        bg = "background:#f9f9f9;" if shaded else ""
        return (
            f'<tr style="{bg}">'
            f'<td style="padding:10px 12px; color:#555; width:160px; '
            f'border-bottom:1px solid #eee;"><strong>{label}</strong></td>'
            f'<td style="padding:10px 12px; border-bottom:1px solid #eee;">{value}</td>'
            f"</tr>"
        )

    priority_badge = (
        f'<span style="background:{priority_color}; color:#fff; padding:3px 12px; '
        f'border-radius:12px; font-size:13px; font-weight:bold;">'
        f'{state.get("ticket_priority", "N/A")}</span>'
    )

    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; color: #333; max-width: 640px; margin: auto; padding: 0;">

  <!-- Header -->
  <div style="background:#1a1a2e; padding:22px 30px; border-radius:8px 8px 0 0;">
    <h2 style="color:#fff; margin:0; font-size:20px;">🎫 New IT Support Ticket</h2>
    <p style="color:#aaa; margin:6px 0 0; font-size:13px;">
      Ticket #{ticket_id} &nbsp;·&nbsp; Raised on {datetime.now().strftime("%d %b %Y at %H:%M")}
    </p>
  </div>

  <!-- Body -->
  <div style="border:1px solid #ddd; border-top:none; padding:24px 30px; border-radius:0 0 8px 8px;">

    <!-- Ticket Info -->
    <h3 style="color:#1a1a2e; margin:0 0 10px;">📋 Ticket Information</h3>
    <table style="width:100%; border-collapse:collapse; border:1px solid #eee; border-radius:6px;">
      {row("Title",    state.get("ticket_title",    "N/A"))}
      {row("Priority", priority_badge,               shaded=True)}
      {row("Category", state.get("ticket_category", "N/A"))}
      {row("Status",   state.get("ticket_status",   "OPEN"), shaded=True)}
    </table>

    <!-- User Info -->
    <h3 style="color:#1a1a2e; margin:24px 0 10px;">👤 Reported By</h3>
    <table style="width:100%; border-collapse:collapse; border:1px solid #eee; border-radius:6px;">
      {row("Name",  state.get("user_name",  "N/A"))}
      {row("Email", state.get("user_email", "N/A"), shaded=True)}
    </table>

    <!-- Issue Description -->
    <h3 style="color:#1a1a2e; margin:24px 0 10px;">🐛 Issue Description</h3>
    <div style="background:#f9f9f9; border:1px solid #eee; border-radius:6px;
                padding:14px 16px; font-size:14px; line-height:1.6;">
      {state.get("user_issue", "N/A").strip()}
    </div>

    <!-- Technical Analysis -->
    <h3 style="color:#1a1a2e; margin:24px 0 10px;">🔍 Technical Analysis</h3>
    <table style="width:100%; border-collapse:collapse; border:1px solid #eee; border-radius:6px;">
      {row("Summary",          state.get("issue_summary",    "N/A"))}
      {row("Category",         state.get("issue_category",   "N/A"), shaded=True)}
      {row("Affected System",  state.get("affected_system",  "N/A"))}
      {row("Severity",         state.get("severity",         "N/A"), shaded=True)}
      {row("Business Impact",  state.get("bussiness_impact", "N/A"))}
    </table>

    <!-- Clarification Q&A (only if present) -->
    {clarification_html}

    <!-- Footer -->
    <hr style="border:none; border-top:1px solid #eee; margin:28px 0 16px;">
    <p style="color:#999; font-size:12px; margin:0; line-height:1.6;">
      This ticket was automatically generated by the <strong>IT Support Agent</strong>.<br>
      Please review, assign to the appropriate team member, and update the ticket status.
    </p>
  </div>

</body>
</html>
"""
    return subject, html_body


def send_ticket_email(state: dict) -> bool:
    """
    Send the ticket email to the admin team via SMTP.
    Reads credentials from environment variables.
    Returns True on success, False on failure.

    The user's own email (state['user_email']) is CC'd so they have
    a record that their ticket was raised.

    ── Gmail (active) ───────────────────────────────────────────
      SMTP_HOST     = smtp.gmail.com
      SMTP_PORT     = 587
      SMTP_USER     = you@gmail.com
      SMTP_PASSWORD = your-app-password
      SMTP_FROM     = you@gmail.com
      ADMIN_EMAIL   = admin-team@yourcompany.com

    ── Outlook / Office 365 (swap in when ready) ────────────────
    #   SMTP_HOST     = smtp.office365.com
    #   SMTP_PORT     = 587
    #   SMTP_USER     = you@outlook.com
    #   SMTP_PASSWORD = your-outlook-password
    #   SMTP_FROM     = you@outlook.com
    #   ADMIN_EMAIL   = admin-team@yourcompany.com
    ─────────────────────────────────────────────────────────────
    """
    # ── Gmail config (active) ─────────────────────────────────
    smtp_host     = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port     = int(os.getenv("SMTP_PORT", 587))
    smtp_user     = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_from     = os.getenv("SMTP_FROM", smtp_user)
    admin_email   = os.getenv("ADMIN_EMAIL", "")

    # ── Outlook / Office 365 config (commented out) ───────────
    # smtp_host     = os.getenv("SMTP_HOST", "smtp.office365.com")
    # smtp_port     = int(os.getenv("SMTP_PORT", 587))
    # smtp_user     = os.getenv("SMTP_USER", "")
    # smtp_password = os.getenv("SMTP_PASSWORD", "")
    # smtp_from     = os.getenv("SMTP_FROM", smtp_user)
    # admin_email   = os.getenv("ADMIN_EMAIL", "")
    # ──────────────────────────────────────────────────────────

    if not all([smtp_user, smtp_password, admin_email]):
        print("⚠️  SMTP credentials not set — skipping email. "
              "Add SMTP_USER, SMTP_PASSWORD, ADMIN_EMAIL to your .env file.")
        return False

    subject, html_body = _build_ticket_email(state)

    user_email = state.get("user_email", "")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = smtp_from
    msg["To"]      = admin_email
    if user_email:
        msg["Cc"]  = user_email          # CC the user so they have a ticket reference
    msg.attach(MIMEText(html_body, "html"))

    recipients = [admin_email] + ([user_email] if user_email else [])

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_from, recipients, msg.as_string())
        print(f"📧 Ticket email sent to {admin_email}" +
              (f"  (CC: {user_email})" if user_email else ""))
        return True
    except smtplib.SMTPException as exc:
        print(f"❌ Failed to send ticket email: {exc}")
        return False


# ──────────────────────────────────────────────
# State
# ──────────────────────────────────────────────

class SupportAgentState(TypedDict):
    # user info
    user_name: str
    user_email: str
    user_issue: str

    # issue understanding
    issue_summary: str
    issue_category: str
    affected_system: str
    severity: str
    bussiness_impact: str

    # classify
    decision: str
    confidence: float
    reason: str

    # clarification
    needs_clarification: bool
    clarification_questions: List[str]
    clarification_answer: List[str]
    classification_count: int

    # resolution
    resolution_found: bool
    solution_step: List[str]
    knowledge_source: str
    estimation_resolution_time: str

    # knowledge base
    knowledge_cache_hit: bool

    # ticket
    ticket_required: bool
    ticket_title: str
    ticket_description: str
    ticket_priority: str
    ticket_category: str
    ticket_id: str
    ticket_status: str
    ticket_email_sent: bool


# ──────────────────────────────────────────────
# Pydantic Schemas (structured LLM outputs)
# ──────────────────────────────────────────────

class IssueAnalysisSchema(BaseModel):
    issue_summary: str = Field(description="Short summary of the issue")
    issue_category: str = Field(
        description="Category: Installation, Access, Network, Application, Database, "
                    "Configuration, Account, Security, Email, Other"
    )
    affected_system: str = Field(description="System or application impacted")
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    bussiness_impact: str = Field(description="Impact on the user's work or business process")


class ClassificationSchema(BaseModel):
    decision: Literal["USER_SOLVABLE", "ADMIN_REQUIRED", "NEED_MORE_INFO"]
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    reason: str = Field(description="Reason for the decision")


class ClarificationSchema(BaseModel):
    needs_clarification: bool
    clarification_questions: List[str] = Field(description="Questions to ask the user")


class ResolutionSchema(BaseModel):
    resolution_found: bool
    solution_step: List[str] = Field(description="Simple troubleshooting steps")
    knowledge_source: str = Field(description="Knowledge base article or reasoning source")
    estimation_resolution_time: str = Field(description="Estimated time to resolve")


class TicketSchema(BaseModel):
    ticket_required: bool
    ticket_title: str = Field(description="Short ticket title")
    ticket_description: str = Field(description="Detailed ticket description")
    ticket_priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    ticket_category: str = Field(description="Support category")


# ──────────────────────────────────────────────
# LLM + structured output chains
# ──────────────────────────────────────────────

llm = ChatOpenAI(model="gpt-4o-mini")

structured_issue_analysis       = llm.with_structured_output(IssueAnalysisSchema)
structured_classification_issue = llm.with_structured_output(ClassificationSchema)
structured_clarification_issue  = llm.with_structured_output(ClarificationSchema)
structured_resolution           = llm.with_structured_output(ResolutionSchema)
structured_ticket               = llm.with_structured_output(TicketSchema)


# ──────────────────────────────────────────────
# Node functions
# ──────────────────────────────────────────────

def analyse_issue(state: SupportAgentState):
    prompt = f"""
You are an IT Support Analyst.

Extract:
- issue_summary
- issue_category
- affected_system
- severity
- bussiness_impact

Categories:
Installation, Access, Network, Application,
Database, Configuration, Account, Security,
Email, Other

Severity:
LOW      = informational
MEDIUM   = single user issue
HIGH     = important work blocked
CRITICAL = outage, server down, database down

Issue:
{state["user_issue"]}

Clarification answers:
{state["clarification_answer"]}
"""
    result = structured_issue_analysis.invoke(prompt)
    return result.model_dump()


def classify_issue(state: SupportAgentState):
    prompt = f"""
Classify this issue as:

USER_SOLVABLE  – Installation, Configuration, How-to, Browser issues, Self-service actions
ADMIN_REQUIRED – Account unlock, Access request, VPN issue, Server/DB/Network issue, Permission issue
NEED_MORE_INFO – Missing application name, Missing error message, Vague issue

Issue:
{state["user_issue"]}

Summary:
{state["issue_summary"]}
"""
    result = structured_classification_issue.invoke(prompt)
    return result.model_dump()


def ask_clarification(state: SupportAgentState):
    prompt = f"""
Generate up to 5 diagnostic questions for this issue.

Issue:
{state["user_issue"]}

Summary:
{state["issue_summary"]}
"""
    result = structured_clarification_issue.invoke(prompt)

    # Pause the graph and wait for human input
    answers = interrupt({"questions": result.clarification_questions})

    return {
        "needs_clarification": False,
        "clarification_questions": result.clarification_questions,
        "clarification_answer": answers,
        "classification_count": state["classification_count"] + 1,
    }


def check_knowledge_base(state: SupportAgentState):
    """
    Called right after classify_issue when decision == USER_SOLVABLE.
    If a matching entry exists in knowledge.json, load it directly and
    skip the LLM call entirely.
    """
    cached = find_cached_resolution(
        state.get("issue_category", ""),
        state.get("affected_system", ""),
    )
    if cached:
        print("⚡ Cache hit — loading resolution from knowledge.json")
        return {
            "resolution_found":           True,
            "solution_step":              cached["solution_step"],
            "knowledge_source":           cached.get("knowledge_source", "knowledge.json"),
            "estimation_resolution_time": cached.get("estimation_resolution_time", "N/A"),
            "knowledge_cache_hit":        True,
        }

    return {"knowledge_cache_hit": False}


def generate_resolution(state: SupportAgentState):
    # Cache hit: resolution already loaded from knowledge.json — skip LLM
    if state.get("knowledge_cache_hit"):
        return {}

    prompt = f"""
Generate simple user troubleshooting steps.

Rules:
- Max 7 steps
- Simple language
- No admin actions

Issue:
{state["issue_summary"]}

Category:
{state["issue_category"]}
"""
    result = structured_resolution.invoke(prompt)
    resolution = result.model_dump()

    # Persist to knowledge.json for future reuse
    append_to_knowledge({**state, **resolution})

    return resolution


def generate_ticket(state: SupportAgentState):
    prompt = f"""
Create a support ticket.

Include: title, description, priority, category

Issue:
{state["issue_summary"]}

System:
{state["affected_system"]}

Severity:
{state["severity"]}

Impact:
{state["bussiness_impact"]}
"""
    result = structured_ticket.invoke(prompt)
    ticket_data = result.model_dump()

    # Assign a unique ticket ID
    ticket_data["ticket_id"] = f"TKT-{uuid.uuid4().hex[:8].upper()}"
    ticket_data["ticket_status"] = "OPEN"

    return ticket_data


def notify_admin(state: SupportAgentState):
    """
    Send the generated ticket to the admin team via SMTP email.
    Runs after generate_ticket, before final_report.
    """
    success = send_ticket_email(state)
    return {"ticket_email_sent": success}


def final_report(state: SupportAgentState):
    if state["decision"] == "USER_SOLVABLE":
        steps = "\n".join(
            f"{i+1}. {step}" for i, step in enumerate(state["solution_step"])
        )
        return {"final_response": f"Please follow these steps:\n\n{steps}"}

    email_status = "✅ Sent" if state.get("ticket_email_sent") else "⚠️ Not sent (check SMTP config)"
    return {
        "final_response": (
            f"Ticket Generated\n\n"
            f"ID:       {state.get('ticket_id', 'N/A')}\n"
            f"Title:    {state.get('ticket_title', 'N/A')}\n"
            f"Priority: {state.get('ticket_priority', 'N/A')}\n"
            f"Category: {state.get('ticket_category', 'N/A')}\n"
            f"Email:    {email_status}"
        )
    }


# ──────────────────────────────────────────────
# Routing helpers
# ──────────────────────────────────────────────

def route_after_classification(state: SupportAgentState) -> str:
    if state["decision"] == "NEED_MORE_INFO" and state["classification_count"] >= 3:
        return "ADMIN_REQUIRED"
    return state["decision"]


def route_after_knowledge_check(state: SupportAgentState) -> str:
    """Skip LLM resolution if knowledge base already has the answer."""
    if state.get("knowledge_cache_hit"):
        return "final_report"
    return "generate_resolution"


# ──────────────────────────────────────────────
# Build the graph
# ──────────────────────────────────────────────

def build_workflow():
    graph = StateGraph(SupportAgentState)
    memory = MemorySaver()

    graph.add_node("analyse_issue",       analyse_issue)
    graph.add_node("classify_issue",      classify_issue)
    graph.add_node("ask_clarification",   ask_clarification)
    graph.add_node("check_knowledge_base",check_knowledge_base)
    graph.add_node("generate_resolution", generate_resolution)
    graph.add_node("generate_ticket",     generate_ticket)
    graph.add_node("notify_admin",        notify_admin)
    graph.add_node("final_report",        final_report)

    graph.add_edge(START, "analyse_issue")
    graph.add_edge("analyse_issue", "classify_issue")

    graph.add_conditional_edges(
        "classify_issue",
        route_after_classification,
        {
            "USER_SOLVABLE":  "check_knowledge_base",
            "ADMIN_REQUIRED": "generate_ticket",
            "NEED_MORE_INFO": "ask_clarification",
        },
    )

    graph.add_conditional_edges(
        "check_knowledge_base",
        route_after_knowledge_check,
        {
            "generate_resolution": "generate_resolution",
            "final_report":        "final_report",
        },
    )

    graph.add_edge("ask_clarification",   "analyse_issue")
    graph.add_edge("generate_resolution", "final_report")
    graph.add_edge("generate_ticket",     "notify_admin")   # ticket → email admin → report
    graph.add_edge("notify_admin",        "final_report")
    graph.add_edge("final_report",        END)

    return graph.compile(checkpointer=memory)


# ──────────────────────────────────────────────
# Helper: run a single issue end-to-end
# ──────────────────────────────────────────────

def collect_user_info() -> tuple[str, str, str]:
    """
    Interactively collect issue, name, and email from the user in the terminal.
    Returns (issue, user_name, user_email).
    """
    print()
    issue = input("📝 Describe your issue:\n   > ").strip()
    while not issue:
        issue = input("   Please describe your issue: ").strip()

    print()
    user_name = input("👤 Your name: ").strip()
    while not user_name:
        user_name = input("   Name cannot be empty: ").strip()

    print()
    user_email = input("📧 Your email address: ").strip()
    while not user_email or "@" not in user_email:
        user_email = input("   Enter a valid email address: ").strip()

    return issue, user_name, user_email


def run_issue(workflow, issue: str, user_name: str, user_email: str) -> dict:
    """
    Run the support workflow for a given issue.
    If the agent needs clarification (HITL interrupt), prompts the user
    in the terminal and resumes automatically.
    The user's email is used to CC them on any ticket raised to the admin team.
    """
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    initial_state = {
        "user_name":            user_name,
        "user_email":           user_email,
        "user_issue":           issue,
        "clarification_answer": [],
        "classification_count": 0,
    }

    result = workflow.invoke(initial_state, config=config)

    # Handle human-in-the-loop clarification loop
    while "__interrupt__" in result:
        questions = result["__interrupt__"][0].value["questions"]
        print("\n🤖 The agent needs a bit more information:")
        answers = []
        for i, q in enumerate(questions, 1):
            ans = input(f"  Q{i}. {q}\n  Your answer: ").strip()
            answers.append(ans)

        result = workflow.invoke(Command(resume=answers), config=config)

    return result


def print_result(result: dict) -> None:
    """Pretty-print the final result for the user."""
    print(f"\n{'─'*60}")
    print(f"📋 Decision  : {result.get('decision', 'N/A')}")
    print(f"📊 Confidence: {result.get('confidence', 'N/A')}")
    print(f"📝 Summary   : {result.get('issue_summary', 'N/A')}")

    if result.get("decision") == "USER_SOLVABLE":
        source = "knowledge.json (cached)" if result.get("knowledge_cache_hit") else "LLM"
        print(f"\n✅ Resolution Steps  [source: {source}]:")
        for i, step in enumerate(result.get("solution_step", []), 1):
            print(f"   {i}. {step}")
    else:
        print(f"\n🎫 Ticket ID      : {result.get('ticket_id', 'N/A')}")
        print(f"🎫 Ticket Title   : {result.get('ticket_title', 'N/A')}")
        print(f"🎫 Ticket Priority: {result.get('ticket_priority', 'N/A')}")
        print(f"🎫 Ticket Category: {result.get('ticket_category', 'N/A')}")
        email_ok = result.get("ticket_email_sent")
        print(f"📧 Admin notified : {'✅ Sent' if email_ok else '⚠️  Not sent (check SMTP config)'}")
        if result.get("user_email"):
            print(f"📧 CC to you      : {result.get('user_email')}")


def main():
    print("=" * 60)
    print("  IT Support Agent")
    print("=" * 60)

    workflow = build_workflow()

    while True:
        # Step 1: collect issue + user details
        issue, user_name, user_email = collect_user_info()

        print(f"\n⏳ Analysing your issue, please wait...")

        # Step 2: run the workflow
        result = run_issue(workflow, issue, user_name, user_email)

        # Step 3: show result
        print_result(result)

        # Step 4: ask if user wants to raise another issue
        print()
        again = input("\n🔄 Do you have another issue? (yes / no): ").strip().lower()
        if again not in ("yes", "y"):
            print("\n👋 Thank you for using IT Support Agent. Goodbye!")
            break
        print(f"\n{'='*60}")


if __name__ == "__main__":
    main()