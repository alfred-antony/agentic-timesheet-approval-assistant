# ui/app.py - COMPLETELY REDESIGNED

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
from datetime import datetime
from data.db import get_connection
from config.settings import DB_PATH

# Email service
from utils.email_service import send_batch_rejection_emails

# Toggle between mock and real pipeline
USE_MOCK = st.checkbox("Use mock data (UI testing mode)", value=False)

if USE_MOCK:
    from ui.mock_data import get_mock_manager_result as run_manager_pipeline
else:
    from pipeline.manager_pipeline import run_manager_pipeline

st.set_page_config(
    page_title="Timesheet Approval Dashboard",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        font-weight: 700;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    .metric-card h3 {
        color: white;
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
    }
    
    .metric-card p {
        color: rgba(255,255,255,0.9);
        margin: 0.5rem 0 0 0;
        font-size: 0.9rem;
    }
    
    .emp-card {
        border-left: 5px solid #1f77b4;
        padding: 1.5rem;
        margin: 1rem 0;
        border-radius: 8px;
        background: #f8f9fa;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .emp-card-approved {
        border-left: 5px solid #28a745;
        background: #d4edda;
    }
    
    .emp-card-rejected {
        border-left: 5px solid #dc3545;
        background: #f8d7da;
    }
    
    .emp-card h3 {
        margin: 0 0 0.5rem 0;
        color: #495057;
    }
    
    .status-badge {
        display: inline-block;
        padding: 0.75rem 1.5rem;
        border-radius: 8px;
        font-weight: 700;
        font-size: 1.1rem;
        text-align: center;
    }
    
    .status-pending {
        background-color: #e7f3ff;
        color: #004085;
        border: 2px solid #0066cc;
    }
    
    .status-review {
        background-color: #fff3cd;
        color: #856404;
        border: 2px solid #ffc107;
    }
    
    .status-approve {
        background-color: #d4edda;
        color: #155724;
        border: 2px solid #28a745;
    }
    
    .status-approved {
        background-color: #d4edda;
        color: #155724;
        border: 2px solid #28a745;
    }
    
    .status-rejected {
        background-color: #f8d7da;
        color: #721c24;
        border: 2px solid #dc3545;
    }
    
    .week-card {
        padding: 1rem;
        border-radius: 6px;
        margin: 0.5rem 0;
    }
    
    .week-pending {
        background-color: #e7f3ff;
        border-left: 4px solid #0066cc;
    }
    
    .week-approved {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
    }
    
    .week-rejected {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
    }
    
    .sidebar-info {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    
    .sidebar-info p {
        margin: 0.3rem 0;
        color: #333;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar - Manager Info
st.sidebar.title("👤 Manager Dashboard")
st.sidebar.markdown("""
<div class="sidebar-info">
    <p><strong>Manager ID:</strong> EMP001</p>
    <p><strong>Name:</strong> Alfred Antony</p>
    <p><strong>Team:</strong> Software Engineering</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")

# View filter in sidebar
view_filter = st.sidebar.radio(
    "📊 View Filter",
    ["Pending Only", "Approved Only", "Rejected Only", "Partial", "All"]
)

refresh_status = st.sidebar.empty()

# Main Header
st.markdown('<h1 class="main-header">📋 Timesheet Approval Dashboard</h1>', unsafe_allow_html=True)
st.markdown("*Enterprise AI-Powered Timesheet Analysis & Approval*")

# Initialize session state
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = {}
if 'employee_decisions' not in st.session_state:
    st.session_state.employee_decisions = {}  # {employee_id: {weeks: {week_start: status}, overall: status, reason: ""}}
if 'pending_rejections' not in st.session_state:
    st.session_state.pending_rejections = []  # List of rejections to email
if 'last_analyzed' not in st.session_state:
    st.session_state.last_analyzed = None

MANAGER_ID = 1

# Helper functions
def get_employee_status(emp_id, weekly_decisions):
    if emp_id not in st.session_state.employee_decisions:
        return "pending"
    
    overall = st.session_state.employee_decisions[emp_id].get("overall")
    if overall in ("approved", "rejected"):
        return overall
    
    weeks = st.session_state.employee_decisions[emp_id].get("weeks", {})
    
    if not weeks:
        return "pending"
    
    total_weeks = len(weekly_decisions)
    decided_weeks = len(weeks)
    approved_weeks = sum(1 for status in weeks.values() if status == "approved")
    rejected_weeks = sum(1 for status in weeks.values() if status == "rejected")
    
    # ✅ FIX: Only move out of pending when ALL weeks decided
    if decided_weeks < total_weeks:
        return "pending"
    
    if approved_weeks == total_weeks:
        return "approved"
    
    if rejected_weeks == total_weeks:
        return "rejected"
    
    return "partial"

def get_week_status(emp_id, week_start):
    """Get current status of a specific week"""
    if emp_id not in st.session_state.employee_decisions:
        return "pending"
    weeks = st.session_state.employee_decisions[emp_id].get("weeks", {})
    return weeks.get(week_start, "pending")

def update_week_status(emp_id, week_start, status):
    """Update status of a specific week"""
    if emp_id not in st.session_state.employee_decisions:
        st.session_state.employee_decisions[emp_id] = {"weeks": {}, "overall": None}
    st.session_state.employee_decisions[emp_id]["weeks"][week_start] = status

def update_employee_status(emp_id, status, reason=""):
    """Update overall status of employee"""
    if emp_id not in st.session_state.employee_decisions:
        st.session_state.employee_decisions[emp_id] = {"weeks": {}, "overall": None}
    st.session_state.employee_decisions[emp_id]["overall"] = status
    st.session_state.employee_decisions[emp_id]["reason"] = reason

def approve_all_remaining():
    """Approve all pending weeks for all employees"""
    result = st.session_state.analysis_result.get(MANAGER_ID, {})
    employees = result.get("employees", [])
    
    approved_count = 0
    
    for emp in employees:
        if emp.get("status") != "ok":
            continue
        
        emp_id = emp["employee_id"]
        weekly_decisions = emp.get("decisions", {}).get("weekly", [])
        
        for week in weekly_decisions:
            week_start = week["week_start"]
            current_status = get_week_status(emp_id, week_start)
            
            # Only approve if still pending
            if current_status == "pending":
                update_week_status(emp_id, week_start, "approved")
                approved_count += 1
    
    return approved_count

# Analyze Button
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown("### Quick Actions")

with col2:
    if st.button("🚀 Analyze Pending Timesheets", type="primary", width='stretch'):
        with st.spinner("🔍 Analyzing timesheets..."):
            refresh_status.markdown("**Status: Analyzing**")
            result = run_manager_pipeline(MANAGER_ID)
            
            if result.get("status") == "ok":
                st.session_state.analysis_result[MANAGER_ID] = result
                st.session_state.last_analyzed = MANAGER_ID
                # Reset decisions for fresh analysis
                st.session_state.employee_decisions = {}
                st.session_state.pending_rejections = []
                st.rerun()
                refresh_status.markdown("✅ **Analysis Complete**")
            else:
                st.error(f"❌ Pipeline Error: {result.get('error', 'Unknown')}")
                refresh_status.markdown("❌ **Analysis Failed**")

# Results Section
if (st.session_state.last_analyzed == MANAGER_ID and 
    MANAGER_ID in st.session_state.analysis_result):
    
    result = st.session_state.analysis_result[MANAGER_ID]
    
    if result.get("status") == "ok" and result.get("employees"):
        
        # Calculate real-time stats based on current decisions
        all_employees = result.get("employees", [])
        pending_count = 0
        approved_count = 0
        rejected_count = 0
        partial_count = 0
        
        for emp in all_employees:
            if emp.get("status") != "ok":
                continue
            
            weekly_decisions = emp.get("decisions", {}).get("weekly", [])
            status = get_employee_status(emp["employee_id"], weekly_decisions)
            
            if status == "approved":
                approved_count += 1
            elif status == "rejected":
                rejected_count += 1
            elif status == "partial":
                partial_count += 1
            else:
                pending_count += 1
        
        # Team Summary
        st.markdown("## 📊 Team Summary")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card" style="background: #2c3e50; border: 2px solid #34495e;">
                <h3>{len(all_employees)}</h3>
                <p>Total Employees</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card" style="background: #5d6d7e; border: 2px solid #707b8a;">
                <h3>{pending_count}</h3>
                <p>⏳ Pending</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card" style="background: #f39c12; border: 2px solid #d68910;">
                <h3>{partial_count}</h3>
                <p>⚠️ Partial</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card" style="background: #27ae60; border: 2px solid #229954;">
                <h3>{approved_count}</h3>
                <p>✅ Approved</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col5:
            st.markdown(f"""
            <div class="metric-card" style="background: #e74c3c; border: 2px solid #c0392b;">
                <h3>{rejected_count}</h3>
                <p>❌ Rejected</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Bulk Actions
        st.markdown("### 🎯 Bulk Actions")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("✅ APPROVE ALL REMAINING", type="primary", width='stretch'):
                approved = approve_all_remaining()
                st.success(f"✅ Approved {approved} pending week(s)")
                st.rerun()
        
        with col2:
            # Count pending rejections
            pending_rejection_count = len(st.session_state.pending_rejections)
            if pending_rejection_count > 0:
                if st.button(f"📧 Send {pending_rejection_count} Email(s)", width='stretch'):
                    with st.spinner("Sending emails..."):
                        result = send_batch_rejection_emails(st.session_state.pending_rejections)
                        
                        if result["sent"] > 0:
                            st.success(f"✅ Successfully sent {result['sent']} email(s)")
                        
                        if result["failed"] > 0:
                            st.error(f"❌ Failed to send {result['failed']} email(s)")
                        
                        st.session_state.pending_rejections = []
                        st.rerun()
            else:
                st.button("📧 No Pending Emails", disabled=True, width='stretch')
        
        st.markdown("---")
        
        # Pending Rejections Summary (moved here - before employee list)
        if st.session_state.pending_rejections:
            st.markdown("## 📧 Queued Rejection Emails")
            
            # Build summary table
            rejection_summary = []
            for rejection in st.session_state.pending_rejections:
                weeks = rejection["rejection_data"]["weeks"]
                reason = rejection["rejection_data"].get("overall_reason", "")
                
                # ✅ NEW: Extract violation reasons
                violation_reasons = []
                for w in weeks:
                    week_reason = w.get("reason", "")
                    if week_reason and week_reason not in violation_reasons:
                        violation_reasons.append(week_reason)
                
                if violation_reasons:
                    violations_display = ", ".join(violation_reasons[:3])
                    if len(violation_reasons) > 3:
                        violations_display += f" (+{len(violation_reasons)-3} more)"
                else:
                    violations_display = "Manager rejected"
                
                rejection_summary.append({
                    "Employee": rejection["employee_name"],
                    "Weeks": ", ".join([w["week"] for w in weeks]),
                    "Violations": violations_display,  # ✅ NEW COLUMN
                    "Manager Note": reason if reason else "—"
                })
            
            rejection_df = pd.DataFrame(rejection_summary)
            st.dataframe(rejection_df, width='stretch', hide_index=True)
            
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.button("📤 Send All Emails Now", type="primary", use_container_width=True):
                    with st.spinner("Sending emails..."):
                        result_email = send_batch_rejection_emails(st.session_state.pending_rejections)
                        
                        # Store results in session state for persistent display
                        st.session_state.email_results = result_email
                        st.session_state.show_email_results = True
                        
                        # Clear queue
                        st.session_state.pending_rejections = []
            
            # Show persistent email results with close button
            if st.session_state.get("show_email_results", False):
                email_results = st.session_state.get("email_results", {})
                
                st.markdown("---")
                st.markdown("### 📧 Email Send Results")
                
                if email_results.get("sent", 0) > 0:
                    st.success(f"✅ **Successfully sent {email_results['sent']} email(s) to employees!**")
                    
                    # Show who received emails
                    with st.expander("📋 View Recipients", expanded=True):
                        for r in email_results.get("results", []):
                            if r.get("success"):
                                st.write(f"✅ **{r['employee']}** → {r.get('recipient', 'N/A')}")
                
                if email_results.get("failed", 0) > 0:
                    st.error(f"❌ **Failed to send {email_results['failed']} email(s)**")
                    
                    with st.expander("⚠️ View Failures", expanded=True):
                        for r in email_results.get("results", []):
                            if not r.get("success"):
                                st.write(f"❌ **{r['employee']}**: {r.get('error', 'Unknown error')}")
                
                # Close button
                if st.button("✓ Continue", type="primary", use_container_width=True):
                    st.session_state.show_email_results = False
                    st.rerun()
                
                st.markdown("---")
            
            with col2:
                if st.button("🗑️ Clear Queue", width='stretch'):
                    st.session_state.pending_rejections = []
                    st.rerun()
            
            st.markdown("---")
        
        # Filter employees based on view selection
        filtered_employees = []
        for emp in all_employees:
            if emp.get("status") != "ok":
                continue
            
            weekly_decisions = emp.get("decisions", {}).get("weekly", [])
            emp_status = get_employee_status(emp["employee_id"], weekly_decisions)
            
            if view_filter == "Pending Only" and emp_status == "pending":
                filtered_employees.append(emp)
            elif view_filter == "Approved Only" and emp_status == "approved":
                filtered_employees.append(emp)
            elif view_filter == "Rejected Only" and emp_status == "rejected":
                filtered_employees.append(emp)
            elif view_filter == "Partial" and emp_status == "partial":
                filtered_employees.append(emp)
            elif view_filter == "All":
                filtered_employees.append(emp)
        
        # Employee Review Section
        st.markdown(f"## 👥 Employee Review ({view_filter})")
        
        if not filtered_employees:
            st.info(f"No employees in '{view_filter}' category")
        
        # COMPLETE EMPLOYEE CARD SECTION - REPLACE IN YOUR UI
        # Find the line: for emp in filtered_employees:
        # Replace everything from there until st.markdown("---") at the end of the loop
        # This includes ALL the missing parts

        for emp in filtered_employees:
            emp_name = emp.get("employee_name", "Unknown")
            emp_code = emp.get("employee_code", "N/A")
            emp_id = emp.get("employee_id", "")
            
            decisions = emp.get("decisions", {})
            overall = decisions.get("overall", {"decision": "UNKNOWN"})
            weekly_decisions = decisions.get("weekly", [])
            
            # Get current status
            emp_status_current = get_employee_status(emp_id, weekly_decisions)
            
            # Determine card styling
            if emp_status_current == "approved":
                card_class = "emp-card emp-card-approved"
                status_badge_class = "status-approved"
                status_text = "APPROVED ✅"
            elif emp_status_current == "rejected":
                card_class = "emp-card emp-card-rejected"
                status_badge_class = "status-rejected"
                status_text = "REJECTED ❌"
            elif emp_status_current == "partial":
                card_class = "emp-card"
                status_badge_class = "status-pending"
                weeks = st.session_state.employee_decisions.get(emp_id, {}).get("weeks", {})
                approved = sum(1 for s in weeks.values() if s == "approved")
                rejected = sum(1 for s in weeks.values() if s == "rejected")
                status_text = f"PARTIAL ({approved}✅ {rejected}❌ / {len(weekly_decisions)})"
            else:
                card_class = "emp-card"
                decision_text = overall.get("decision", "UNKNOWN")
                if decision_text == "REVIEW":
                    status_badge_class = "status-review"
                    status_text = "NEEDS REVIEW ⚠️"
                else:
                    status_badge_class = "status-pending"
                    status_text = "PENDING REVIEW ⏳"
            
            # Employee Card
            st.markdown(f'''
            <div class="{card_class}">
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <div>
                        <h3>{emp_name}</h3>
                        <small style='color: #666;'>{emp_code}</small>
                    </div>
                    <div class="status-badge {status_badge_class}">
                        {status_text}
                    </div>
                </div>
            </div>
            ''', unsafe_allow_html=True)
            
            # Action buttons (only for pending/partial)
            if emp_status_current in ("pending", "partial"):
                col1, col2, col3 = st.columns([1, 1, 2])
                
                with col1:
                    if st.button(f"✅ APPROVE ALL", key=f"approve_emp_{emp_id}", width="stretch"):
                        for week in weekly_decisions:
                            if get_week_status(emp_id, week["week_start"]) == "pending":
                                update_week_status(emp_id, week["week_start"], "approved")
                        st.rerun()
                
                with col2:
                    dialog_key = f"reject_dialog_{emp_id}"
                    if st.button(f"❌ REJECT ALL", key=f"reject_emp_{emp_id}", width="stretch"):
                        st.session_state[dialog_key] = True
                
                # Rejection reason dialog
                if st.session_state.get(dialog_key, False):
                    with st.form(key=f"rejection_form_{emp_id}"):
                        st.markdown(f"**Rejecting all timesheets for {emp_name}**")
                        rejection_reason = st.text_area(
                            "Manager's Note (will be included in email):",
                            placeholder="e.g., Multiple policy violations. Please review and resubmit.",
                            height=100,
                            key=f"reason_text_{emp_id}"
                        )
                        
                        col_submit, col_cancel = st.columns(2)
                        
                        with col_submit:
                            submit_rejection = st.form_submit_button("Confirm Rejection", type="primary", width="stretch")
                        
                        with col_cancel:
                            cancel_rejection = st.form_submit_button("Cancel", width="stretch")
                        
                        if submit_rejection:
                            # Mark all weeks as rejected
                            for week in weekly_decisions:
                                update_week_status(emp_id, week["week_start"], "rejected")
                            
                            update_employee_status(emp_id, "rejected", rejection_reason)
                            
                            # Add to pending rejections for email
                            st.session_state.pending_rejections.append({
                                "employee_id": emp_id,
                                "employee_name": emp_name,
                                "rejection_data": {
                                    "weeks": [
                                        {"week": w["week_start"], "reason": w.get("reason", "Manager review required")}
                                        for w in weekly_decisions
                                    ],
                                    "overall_reason": rejection_reason
                                }
                            })
                            
                            st.session_state[dialog_key] = False
                            st.rerun()
                        
                        if cancel_rejection:
                            st.session_state[dialog_key] = False
                            st.rerun()
            
            # ============================================
            # ✅ SUMMARY SECTION (AI-generated)
            # ============================================
            st.markdown("**📝 AI Summary**")
            summary_text = emp.get("summary", "No summary available")
            st.info(summary_text)
            
            # ============================================
            # ✅ AGENT ASSESSMENT SECTION (THIS WAS MISSING!)
            # ============================================
            agent_assessment = emp.get("decisions", {}).get("agent_assessment", {})
            
            if agent_assessment and agent_assessment.get("pattern"):
                st.markdown("**🤖 Agent Assessment**")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    pattern = agent_assessment.get("pattern", "Normal behavior")
                    # Clean up pattern text
                    pattern_display = pattern.replace("_", " ").title()
                    if len(pattern_display) > 30:
                        pattern_display = pattern_display[:27] + "..."
                    st.metric("Behavior Pattern", pattern_display)
                
                with col2:
                    risk = agent_assessment.get("risk", "low")
                    risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk.lower(), "⚪")
                    st.metric("Risk Level", f"{risk_emoji} {risk.upper()}")
                
                with col3:
                    rec = agent_assessment.get("recommendation", "review")
                    rec_display = rec.replace("_", " ").title()
                    st.metric("Recommendation", rec_display)
            
            # ============================================
            # ✅ WEEKLY BREAKDOWN
            # ============================================
            if weekly_decisions:
                st.markdown("**📅 Weekly Decisions**")
                
                for week in weekly_decisions:
                    week_start = week.get("week_start", "Unknown")
                    week_status_current = get_week_status(emp_id, week_start)
                    
                    # Determine badge styling
                    if week_status_current == "approved":
                        week_badge = "✅ APPROVED"
                    elif week_status_current == "rejected":
                        week_badge = "❌ REJECTED"
                    else:
                        decision = week.get("decision", "PENDING")
                        reason = week.get("reason", "")
                        
                        if decision == "REVIEW" and reason:
                            week_badge = f"⚠️ REVIEW - {reason}"
                        elif decision == "REVIEW":
                            week_badge = "⚠️ REVIEW"
                        else:
                            week_badge = "⏳ PENDING"
                    
                    # Expander with entries
                    with st.expander(f"{week_start} - {week_badge}"):
                        entries = week.get("entries", [])
                        
                        if entries and isinstance(entries, list):
                            clean_entries = []
                            for entry in entries:
                                if isinstance(entry, dict):
                                    clean_entries.append({
                                        "date": str(entry.get("date", "")),
                                        "type": str(entry.get("type", "")),
                                        "hours": float(entry.get("hours", 0))
                                    })
                            
                            if clean_entries:
                                entries_df = pd.DataFrame(clean_entries)
                                st.dataframe(
                                    entries_df,
                                    width="stretch",
                                    hide_index=True,
                                    column_config={
                                        "date": "Date",
                                        "type": "Type",
                                        "hours": st.column_config.NumberColumn("Hours", format="%.1f")
                                    }
                                )
                            else:
                                st.info("No valid entries found")
                        else:
                            st.info("No entries found for this week")
                        
                        # Reject button (only for pending weeks in pending/partial employees)
                        if emp_status_current in ("pending", "partial") and week_status_current == "pending":
                            if st.button(f"❌ Reject Week", key=f"reject_week_{emp_id}_{week_start}", width="stretch"):
                                update_week_status(emp_id, week_start, "rejected")
                                
                                # Add to rejection queue
                                st.session_state.pending_rejections.append({
                                    "employee_id": emp_id,
                                    "employee_name": emp_name,
                                    "rejection_data": {
                                        "weeks": [{"week": week_start, "reason": week.get("reason", "Manager review required")}],
                                        "overall_reason": ""
                                    }
                                })
                                
                                st.rerun()
            
            st.markdown("---")
        
        st.success("🎉 Dashboard Ready!")
    
    else:
        st.error(f"❌ Analysis failed: {result.get('error', 'Unknown')}")

else:
    st.info("👆 Click **Analyze Pending Timesheets** to begin")
    
    # st.markdown("### 🚀 New Workflow - Easier for Managers:")
    st.markdown("### How to use:")
    st.markdown("""
    1. **Analyze**: Process all pending timesheets
    2. **Reject Only**: Review each employee and **only reject** problem weeks/employees
    3. **Approve Remaining**: Click "✅ APPROVE ALL REMAINING" to bulk approve everything else
    4. **Send Emails**: Review rejection queue, then click "📤 Send All Emails"
    5. **Filter Views**: 
       - **Pending Only** → Focus on undecided items
       - **Partial** → Employees with mixed decisions
       - **Approved/Rejected** → Review completed decisions
    
    **Key Benefits:**
    - No need to click approve for every employee
    - Focus on problems first, bulk approve the rest
    - Visual status: Cards change color as you decide
    - Emails sent in one batch at the end
    """)

# Footer
st.markdown("---")
st.markdown("*Enterprise Timesheet Approval System | Powered by AI*")