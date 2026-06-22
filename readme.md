# AI Support Ticketing Agent (LangGraph)

## Overview

This project is an AI-powered Support Ticketing Agent built using LangGraph. The goal of the system is to assist users with application-related issues, installation problems, access issues, configuration errors, and general troubleshooting requests.

Instead of creating a support ticket for every request, the agent first analyzes the issue and determines whether the user can resolve the problem independently or whether administrator intervention is required.

The system aims to reduce unnecessary ticket creation, improve response times, and provide users with immediate assistance whenever possible.

---

# Problem Statement

In many organizations, users raise support tickets for issues that could be resolved through simple troubleshooting steps. This increases the workload on support teams and delays resolution for critical issues.

This agent addresses that problem by:

1. Understanding the user's issue.
2. Classifying the issue type.
3. Determining whether the issue is:

   * User Solvable
   * Requires Administrator Support
   * Requires More Information
4. Guiding the user with simple resolution steps when possible.
5. Creating a support ticket only when necessary.

---

# Technology Stack

* Python
* LangGraph
* LangChain
* Pydantic
* OpenAI / Compatible LLM
* Future Integrations:

  * Jira
  * ServiceNow
  * Email Notifications
  * Internal Knowledge Base
  * Vector Database

---

# Workflow

The workflow follows a decision-based support process.

```text
START
   │
   ▼
Analyse Issue
   │
   ▼
Classify Issue
   │
   ├── USER_SOLVABLE
   │         │
   │         ▼
   │   Generate Resolution
   │         │
   │         ▼
   │    Final Report
   │
   ├── ADMIN_REQUIRED
   │         │
   │         ▼
   │   Generate Ticket
   │         │
   │         ▼
   │    Final Report
   │
   └── NEED_MORE_INFO
             │
             ▼
      Ask Clarification
             │
             ▼
       Analyse Again
```

---

# State Design

The application uses a centralized LangGraph state called `SupportAgentState`.

## User Information

Stores information provided by the user.

```python
user_name
user_email
user_issue
```

---

## Issue Understanding

Stores the AI-generated understanding of the problem.

```python
issue_summary
issue_category
affected_system
severity
bussiness_impact
```

---

## Classification

Stores the decision made by the classifier.

```python
decision
confidence
reason
```

Possible values:

```text
USER_SOLVABLE
ADMIN_REQUIRED
NEED_MORE_INFO
```

---

## Clarification

Used when additional information is required.

```python
needs_clarification
clarification_questions
clarification_answer
classification_count
```

---

## Resolution

Stores troubleshooting information for user-solvable issues.

```python
resolution_found
solution_step
knowledge_source
estimation_resolution_time
```

---

## Ticket Information

Stores information required for ticket generation.

```python
ticket_required
ticket_title
ticket_description
ticket_priority
ticket_category
ticket_id
ticket_status
```

---

# Structured Output Schemas

To ensure predictable and validated outputs from the LLM, each node uses a dedicated Pydantic schema.

---

## IssueAnalysisSchema

Purpose:
Extract structured issue information from the user's query.

Output:

```python
issue_summary
issue_category
affected_system
severity
bussiness_impact
```

---

## ClassificationSchema

Purpose:
Determine the next action for the workflow.

Output:

```python
decision
confidence
reason
```

Decision Values:

```text
USER_SOLVABLE
ADMIN_REQUIRED
NEED_MORE_INFO
```

---

## ClarificationSchema

Purpose:
Generate follow-up questions when the issue lacks sufficient detail.

Output:

```python
needs_clarification
clarification_questions
```

---

## ResolutionSchema

Purpose:
Generate simple troubleshooting steps for user-solvable issues.

Output:

```python
resolution_found
solution_step
knowledge_source
estimation_resolution_time
```

---

## TicketSchema

Purpose:
Generate support ticket information for issues requiring administrator intervention.

Output:

```python
ticket_required
ticket_title
ticket_description
ticket_priority
ticket_category
```

---

## TicketResponseSchema

Purpose:
Capture the response from the ticket creation system.

Output:

```python
ticket_id
ticket_status
```

---

# LangGraph Nodes

## 1. analyse_issue

Purpose:

* Understand the issue.
* Identify category and severity.
* Extract business impact.

Schema Used:

```python
IssueAnalysisSchema
```

Updates State:

```python
issue_summary
issue_category
affected_system
severity
bussiness_impact
```

---

## 2. classify_issue

Purpose:

Determine the next workflow path.

Schema Used:

```python
ClassificationSchema
```

Updates State:

```python
decision
confidence
reason
```

---

## 3. ask_clarification

Purpose:

Ask follow-up questions when the issue is not clear.

Schema Used:

```python
ClarificationSchema
```

Updates State:

```python
needs_clarification
clarification_questions
```

---

## 4. generate_resolution

Purpose:

Provide user-friendly troubleshooting instructions.

Schema Used:

```python
ResolutionSchema
```

Updates State:

```python
resolution_found
solution_step
knowledge_source
estimation_resolution_time
```

---

## 5. generate_ticket

Purpose:

Prepare ticket information for admin-level issues.

Schema Used:

```python
TicketSchema
```

Updates State:

```python
ticket_required
ticket_title
ticket_description
ticket_priority
ticket_category
```

---

## 6. final_report

Purpose:

Generate the final response shown to the user.

Possible Outputs:

### User Solvable

```text
Issue analyzed successfully.

Please follow the suggested troubleshooting steps.

Thank you for contacting support.
```

### Admin Required

```text
Your issue requires administrator assistance.

A support ticket has been generated.

Ticket ID: INC-12345

Thank you for contacting support.
```

---

# Routing Logic

The workflow uses a router after issue classification.

```python
decision
```

Possible routes:

```text
USER_SOLVABLE  → generate_resolution
ADMIN_REQUIRED → generate_ticket
NEED_MORE_INFO → ask_clarification
```

---

# Clarification Loop

If the classifier determines that additional information is required:

1. Clarification questions are generated.
2. User provides responses.
3. Issue is analyzed again.
4. Classification is repeated.

This continues until:

* The issue becomes user-solvable.
* The issue requires admin support.
* Maximum clarification attempts are reached.

---

# Current Project Status

Completed:

* State Design
* Workflow Design
* Node Identification
* Routing Logic
* Structured Output Schemas
* LangGraph Structure Design
* Conditional Routing Strategy

Pending:

* Node Implementations
* Prompt Engineering
* Ticket Creation Tool
* Email Generation
* Knowledge Base Integration
* Database Persistence
* Human-in-the-loop Support
* Jira / ServiceNow Integration
* Frontend Interface

---

# Future Enhancements

1. Ticket Auto Assignment
2. Knowledge Base Search
3. RAG-based Troubleshooting
4. Email Notifications
5. SLA Tracking
6. Escalation Rules
7. Multi-Agent Architecture
8. Conversation History Persistence
9. Analytics Dashboard
10. Admin Review Workflow

---

# Goal

Create an intelligent support system that resolves simple issues automatically, gathers missing information when required, and raises tickets only when administrator involvement is necessary, thereby reducing support workload and improving user experience.
