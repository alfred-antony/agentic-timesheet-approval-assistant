# 🧠 Agentic AI Timesheet Approval System

AI-assisted decision support system for enterprise timesheet approvals.

This project demonstrates how rule-based validation and focused AI reasoning can assist managers in reviewing employee timesheets — while keeping final approval fully human-controlled.

---

## ✨ Overview

Managers often need to review multiple employee timesheets across weeks, checking:

* Policy compliance
* Holiday and leave mismatches
* Workload consistency
* Overload or underutilization

This system automates detection and analysis, then provides structured recommendations:

* Weekly decision (APPROVE / REVIEW)
* Overall monthly decision
* Manager-friendly behavioral summary
* Email notification for rejected cases

The system assists — it does not replace — managerial judgment.

---

## 🏗 Architecture

```
timesheet_ai/
│
├── data/              # Database access & data fetching
├── rules/             # Policy engine & workload metrics
├── ai/                # Summary & decision agents
├── pipeline/          # Employee & manager pipelines
├── ui/                # Streamlit dashboard
├── config/
├── main.py
└── requirements.txt
```

---

## ⚙️ Workflow

When a manager clicks **Analyze Pending Timesheets**:

1. Fetch submitted weekly timesheets (4 weeks per employee)
2. Run rule-based policy validation
3. Compute workload metrics
4. Generate AI-based monthly interpretation
5. Produce:

   * Weekly decisions
   * Overall decision
   * Manager summary
6. Send automated email for rejected cases

---

## 🧩 System Components

### 🔹 Data Layer

* SQLite database
* Employees, projects, timesheets, holidays, leaves
* Data agent fetches submitted weeks

---

### 🔹 Policy Engine (Deterministic)

No LLM used here.

Checks:

* Worked on holiday
* Leave without approval
* Worked during approved leave
* Fake holiday entry
* Zero-hour work entry
* Impossible hour entry

---

### 🔹 Monthly Metrics Engine

* Total weekly hours
* Average workload
* Overload / underutilization signals
* Stability patterns

---

### 🔹 AI Layer

Responsible for:

* Monthly behavioral interpretation
* Manager-readable summary
* Review explanation (only when needed)

LLM usage is minimal and controlled.

---

### 🔹 Manager Dashboard (Streamlit)

* Multi-employee overview
* Expandable employee cards
* Weekly breakdown view
* Approve / Reject buttons
* Approve All option
* Email automation for rejected employees

---

## 📊 Output Structure

For each employee:

* Overall decision
* Weekly decisions
* Violation details (if any)
* Monthly summary
* Email status (if rejected)

---

## 🛠 Tech Stack

* Python
* SQLite
* Streamlit
* Groq API (LLaMA 3.1 8B)
* Pandas

---

## 🚀 Future Enhancements

* Cross-month behavioral tracking
* Risk scoring model
* Escalation workflow
* Audit logs
* HR system integration
