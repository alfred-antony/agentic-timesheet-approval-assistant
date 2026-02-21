# data/data_agent.py

from collections import defaultdict
from data.db import get_connection


def fetch_employee_month(employee_id):
    """
    Fetch all submitted weekly timesheets for an employee
    Returns structured monthly dataset
    """

    conn = get_connection()
    cur = conn.cursor()

    # -------------------------
    # Fetch submitted weeks
    # -------------------------
    cur.execute("""
        SELECT id, week_start_date
        FROM timesheets
        WHERE employee_id = ?
        AND status = 'Submitted'
        ORDER BY week_start_date
    """, (employee_id,))

    weeks = cur.fetchall()

    if not weeks:
        conn.close()
        return None

    week_map = {w[0]: w[1] for w in weeks}

    # -------------------------
    # Fetch entries
    # -------------------------
    placeholders = ",".join("?" * len(week_map))

    cur.execute(f"""
        SELECT timesheet_id, entry_date, entry_type, hours_worked
        FROM timesheet_entries
        WHERE timesheet_id IN ({placeholders})
    """, tuple(week_map.keys()))

    entries = cur.fetchall()

    week_entries = defaultdict(list)

    for tid, date, etype, hours in entries:
        week_entries[tid].append({
            "date": date,
            "type": etype,
            "hours": hours
        })

    # -------------------------
    # Fetch leave records
    # -------------------------
    cur.execute("""
        SELECT leave_date, approved
        FROM employee_leaves
        WHERE employee_id = ?
    """, (employee_id,))

    leaves = cur.fetchall()
    leave_map = {d: a for d, a in leaves}

    # -------------------------
    # Fetch holidays
    # -------------------------
    cur.execute("SELECT holiday_date FROM holidays")
    holidays = {r[0] for r in cur.fetchall()}

    conn.close()

    # -------------------------
    # Build monthly payload
    # -------------------------
    result = {
        "employee_id": employee_id,
        "weeks": []
    }

    for tid, start in week_map.items():
        result["weeks"].append({
            "week_start": start,
            "entries": week_entries[tid],
            "leave_map": leave_map,
            "holidays": list(holidays)
        })

    return result


def fetch_employees_under_manager(manager_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT e.id, e.employee_code, e.employee_name
        FROM project_allocations pa
        JOIN employees e ON pa.employee_id = e.id
        WHERE pa.manager_id = ?
    """, (manager_id,))

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "employee_id": r[0],
            "employee_code": r[1],
            "employee_name": r[2]
        }
        for r in rows
    ]