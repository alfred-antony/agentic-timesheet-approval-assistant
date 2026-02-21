# rules/policy_engine.py

from datetime import datetime


def is_weekend(date_str):
    d = datetime.fromisoformat(date_str)
    return d.weekday() >= 5


def analyze_week(week, context):
    """
    Analyze one week of entries
    Returns structured weekly report
    """

    holidays = set(context["holidays"])
    leave_map = context["leave_map"]

    violations = []
    overload_days = []
    under_days = []

    work_hours = []

    for e in week["entries"]:
        date = e["date"]
        etype = e["type"]
        hours = e["hours"]

        # ---------------------
        # Collect workload
        # ---------------------
        if etype == "WORK":
            work_hours.append(hours)

            if hours > 10:
                overload_days.append(date)

            if hours < 4 and hours > 0:  # Only flag if some work but too little
                under_days.append(date)

        # ---------------------
        # Policy checks
        # ---------------------

        # worked on holiday
        if etype == "WORK" and date in holidays:
            violations.append({
                "type": "worked_on_holiday",
                "date": date,
                "hours": hours
            })

        # leave without request
        if etype == "LEAVE" and date not in leave_map:
            violations.append({
                "type": "leave_without_request",
                "date": date
            })

        # rejected leave used
        if etype == "LEAVE" and leave_map.get(date) == 0:
            violations.append({
                "type": "rejected_leave_used",
                "date": date
            })

        # fake holiday entry
        if etype == "HOLIDAY" and date not in holidays and not is_weekend(date):
            violations.append({
                "type": "fake_holiday_entry",
                "date": date
            })

        # impossible shift
        if etype == "WORK" and hours > 12:
            violations.append({
                "type": "impossible_shift",
                "date": date,
                "hours": hours
            })

        # zero work hour
        if etype == "WORK" and hours == 0:
            violations.append({
                "type": "zero_hour_work_entry",
                "date": date
            })

    # ---------------------
    # Check for no work entries (NEW)
    # ---------------------
    if not work_hours:
        violations.append({
            "type": "no_work_entries",
            "date": week["week_start"]
        })

    # ---------------------
    # Weekly metrics
    # ---------------------
    total = sum(work_hours)
    avg = total / len(work_hours) if work_hours else 0
    variation = max(work_hours) - min(work_hours) if len(work_hours) > 1 else 0

    weekly_decision = "REVIEW" if violations else "APPROVE"

    return {
        "week_start": week["week_start"],
        "violations": violations,
        "signals": {
            "overload_days": overload_days,
            "underutilized_days": under_days,
            "variation": round(variation, 2)
        },
        "metrics": {
            "total_hours": round(total, 2),
            "avg_hours": round(avg, 2),
            "working_days": len(work_hours)
        },
        "decision": weekly_decision,
        "entries": week.get("entries", [])  # ✅ Preserve original entries
    }


def run_policy_engine(month_data):
    """
    Analyze full employee month
    """

    context = {
        "holidays": month_data["weeks"][0]["holidays"],
        "leave_map": month_data["weeks"][0]["leave_map"]
    }

    weekly_reports = []

    for week in month_data["weeks"]:
        report = analyze_week(week, context)
        weekly_reports.append(report)

    return {
        "employee_id": month_data["employee_id"],
        "weeks": weekly_reports
    }