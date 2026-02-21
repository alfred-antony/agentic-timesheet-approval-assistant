# utils/email_service.py

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv
import sqlite3
from config.settings import DB_PATH

load_dotenv()

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


def get_employee_email(employee_id):
    """
    Fetch employee email from database
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT email FROM employees WHERE id = ?", (employee_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None


def generate_rejection_email_body(employee_name, rejection_data):
    """
    Generate professional email body for timesheet rejection
    
    Args:
        employee_name: str
        rejection_data: dict with 'weeks' list and optional 'overall_reason'
    """
    
    weeks = rejection_data.get("weeks", [])
    overall_reason = rejection_data.get("overall_reason", "")
    
    # Build week details
    week_details = []
    for week_info in weeks:
        week_start = week_info.get("week", "Unknown")
        reason = week_info.get("reason", "Manager review required")
        week_details.append(f"  • Week of {week_start}: {reason}")
    
    week_details_text = "\n".join(week_details) if week_details else "  • All submitted weeks"
    
    # Build email body
    body = f"""Dear {employee_name},

Your timesheet submission has been reviewed and requires revision before approval.

REJECTED TIMESHEET(S):
{week_details_text}
"""
    
    if overall_reason:
        body += f"""
MANAGER'S NOTE:
{overall_reason}
"""
    
    body += """
NEXT STEPS:
1. Review the flagged items above
2. Make necessary corrections in the timesheet system
3. Resubmit for approval

If you have questions about this rejection, please contact your manager directly.

Best regards,
Timesheet Approval System
HTC Global Services
"""
    
    return body


def send_rejection_email(employee_id, employee_name, rejection_data):
    """
    Send rejection email to employee
    
    Args:
        employee_id: str/int
        employee_name: str
        rejection_data: dict with weeks and optional overall_reason
    
    Returns:
        dict: {"success": bool, "error": str or None}
    """
    
    # Get employee email
    employee_email = get_employee_email(employee_id)
    
    if not employee_email:
        return {
            "success": False,
            "error": f"No email found for employee {employee_name}"
        }
    
    # Check SMTP configuration
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        return {
            "success": False,
            "error": "Email configuration missing (GMAIL_USER or GMAIL_APP_PASSWORD)"
        }
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = employee_email
        msg['Subject'] = f"Timesheet Rejection - Action Required"
        
        # Generate body
        body = generate_rejection_email_body(employee_name, rejection_data)
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        
        print(f"[EMAIL] Sent rejection email to {employee_name} ({employee_email})")
        
        return {
            "success": True,
            "error": None,
            "recipient": employee_email
        }
        
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send to {employee_name}: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


def send_batch_rejection_emails(rejections):
    """
    Send multiple rejection emails
    
    Args:
        rejections: list of dicts with employee_id, employee_name, rejection_data
    
    Returns:
        dict: {"sent": int, "failed": int, "results": list}
    """
    
    sent = 0
    failed = 0
    results = []
    
    for rejection in rejections:
        result = send_rejection_email(
            rejection["employee_id"],
            rejection["employee_name"],
            rejection["rejection_data"]
        )
        
        if result["success"]:
            sent += 1
        else:
            failed += 1
        
        results.append({
            "employee": rejection["employee_name"],
            "success": result["success"],
            "error": result.get("error"),
            "recipient": result.get("recipient")
        })
    
    return {
        "sent": sent,
        "failed": failed,
        "results": results
    }