# 🤖 AI-Powered IT Support Agent

An intelligent **IT Helpdesk Automation Agent** built using **LangGraph**, **Large Language Models (LLMs)**, and **Pydantic Structured Outputs**.

The agent automates the complete IT support lifecycle—from understanding user issues to generating resolutions or creating support tickets—while reducing repetitive work for IT teams.

---

# 📌 Problem Statement

Modern IT support teams face several operational challenges:

- High volume of repetitive support tickets
- Manual ticket classification and routing
- Long Mean Time To Resolution (MTTR)
- Knowledge scattered across documentation and senior engineers
- Repeated troubleshooting for identical issues
- Delayed responses affecting employee productivity

These challenges increase operational costs and reduce IT team efficiency.

---

# 💡 Solution

The AI-Powered IT Support Agent automates IT support using LangGraph workflows and LLM reasoning.

The agent can:

- Understand user issues using Natural Language Processing
- Analyze and classify incidents
- Search previously solved issues from a Knowledge Base
- Ask clarification questions when required
- Generate troubleshooting steps automatically
- Create support tickets for admin-required issues
- Send email notifications to the IT Admin team
- Continuously improve by storing solved issues

---

# 🚀 Features

## Intelligent Issue Analysis

- Extracts issue summary
- Detects affected system
- Identifies issue category
- Determines severity
- Calculates business impact

---

## Intelligent Classification

Issues are classified into:

- USER_SOLVABLE
- ADMIN_REQUIRED
- NEED_MORE_INFO

---

## Human-in-the-Loop

When insufficient information is available, the agent:

- Generates clarification questions
- Waits for user responses
- Re-analyzes the issue

---

## Knowledge Base

The agent maintains a local Knowledge Base (`knowledge.json`).

Before calling the LLM, it searches for existing solutions.

Benefits:

- Faster responses
- Lower LLM cost
- Consistent troubleshooting
- Continuous learning

---

## Automatic Resolution

For user-solvable issues, the agent generates:

- Step-by-step troubleshooting
- Estimated resolution time
- Knowledge source

---

## Automatic Ticket Generation

If admin intervention is required, the agent automatically generates:

- Ticket ID
- Ticket Title
- Description
- Priority
- Category
- Status

---

## Email Notification

Generated tickets are automatically emailed to the IT Admin Team using SMTP.

The reporting user is also CC'd.

---

# 🏗 Architecture

```
                    User
                      │
                      ▼
             Analyse Issue
                      │
                      ▼
             Classify Issue
                      │
      ┌───────────────┴───────────────┐
      │                               │
USER_SOLVABLE                 ADMIN_REQUIRED
      │                               │
      ▼                               ▼
Knowledge Base                 Generate Ticket
      │                               │
Cache Hit?                            ▼
      │                         Send Email
      ▼                               │
Generate Resolution                   ▼
      │                         Final Report
      └───────────────┬───────────────┘
                      ▼
                 Final Response
```

---

# 🔄 Workflow

## Step 1

User submits an issue.

Example:

```
My application is showing HTTP 500 Internal Server Error.
```

---

## Step 2

The agent analyzes:

- Summary
- Category
- Severity
- Business Impact
- Affected System

---

## Step 3

The issue is classified as:

- USER_SOLVABLE
- ADMIN_REQUIRED
- NEED_MORE_INFO

---

## Step 4

If required:

- Ask clarification questions

Example:

- Which application?
- When did the issue start?
- Any error code?

---

## Step 5

Search Knowledge Base

If the issue already exists:

- Return cached solution

Otherwise:

- Generate new solution using LLM

---

## Step 6

If the issue cannot be solved by the user:

- Create support ticket
- Notify Admin Team

---

## Step 7

Return the final response to the user.

---

# 🧠 State Management

The workflow uses a centralized `SupportAgentState`.

Important fields include:

### User Information

- user_name
- user_email
- user_issue

---

### Issue Analysis

- issue_summary
- issue_category
- affected_system
- severity
- business_impact

---

### Classification

- decision
- confidence
- reason

---

### Clarification

- clarification_questions
- clarification_answer

---

### Resolution

- solution_step
- knowledge_source
- estimation_resolution_time

---

### Knowledge Base

- knowledge_cache_hit

---

### Ticket Information

- ticket_id
- ticket_title
- ticket_priority
- ticket_category
- ticket_status
- ticket_email_sent

---

# 🛠 Tech Stack

| Technology | Purpose |
|------------|---------|
| Python | Backend |
| LangGraph | Workflow orchestration |
| LangChain | LLM integration |
| OpenAI GPT | Reasoning |
| Pydantic | Structured Outputs |
| SMTP | Email Notification |
| JSON | Knowledge Base |
| dotenv | Environment Variables |

---

# ⚙ Installation

```bash
git clone https://github.com/Rahul3998/AI-Support-Ticketing-Agent-LangGraph-.git

cd IT-Support-Agent
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

# Environment Variables

Create a `.env`

```env
OPENAI_API_KEY=

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
ADMIN_EMAIL=
```

---

# ▶ Run

```bash
python main.py
```

---

# 📈 Benefits

✅ Faster Issue Resolution

✅ Lower Operational Cost

✅ Reduced Manual Work

✅ Consistent Troubleshooting

✅ Knowledge Reuse

✅ Automatic Ticket Creation

✅ Human-in-the-Loop Support

✅ Enterprise Ready

---

# 🔮 Future Enhancements

- ServiceNow Integration
- Jira Integration
- Microsoft Teams Bot
- Slack Bot
- RAG-based Knowledge Base
- Vector Database
- Multi-language Support
- Voice Assistant
- Dashboard & Analytics

---

# 👨‍💻 Author

**Rahul Adagale**

AI Engineer | Python Developer | LangGraph Developer

---

# ⭐ If you like this project

Please consider giving the repository a ⭐ on GitHub.
