# rules/monthly_metrics.py


def compute_monthly_metrics(policy_report):
    """
    Aggregate weekly policy output into monthly metrics
    """

    weeks = policy_report["weeks"]

    total_violations = 0
    overload_days = 0
    under_days = 0
    weekly_hours = []

    for w in weeks:
        total_violations += len(w["violations"])
        overload_days += len(w["signals"]["overload_days"])
        under_days += len(w["signals"]["underutilized_days"])
        weekly_hours.append(w["metrics"]["total_hours"])

    avg_weekly_hours = sum(weekly_hours) / len(weekly_hours) if weekly_hours else 0

    # variation trend
    if len(weekly_hours) > 1:
        variation_trend = max(weekly_hours) - min(weekly_hours)
    else:
        variation_trend = 0

    # flags
    flags = []

    if total_violations > 1:
        flags.append("repeated_violations")

    if overload_days >= 3:
        flags.append("overload_pattern")

    if under_days >= 3:
        flags.append("underutilization_pattern")

    if variation_trend > 10:
        flags.append("inconsistent_workload")

    return {
        "employee_id": policy_report["employee_id"],
        "summary": {
            "total_weeks": len(weeks),
            "total_violations": total_violations,
            "overload_days": overload_days,
            "underutilized_days": under_days,
            "avg_weekly_hours": round(avg_weekly_hours, 2),
            "variation_trend": round(variation_trend, 2),
            "flags": flags
        }
    }
