# pipeline/employee_pipeline.py - OPTIMIZED VERSION

from data.data_agent import fetch_employee_month
from rules.policy_engine import run_policy_engine
from rules.monthly_metrics import compute_monthly_metrics
from ai.agentic_decision_agent import run_batch_agentic_decision


def run_employee_pipeline(employee_id):

    result = {
        "employee_id": employee_id,
        "status": "ok",
        "weekly_reports": [],
        "monthly_metrics": None,
        "summary": None,
        "decisions": None,
        "error": None
    }

    try:
        print(f"[DEBUG] Employee {employee_id}: Fetching data...")
        
        # Step 1 — fetch data
        month_data = fetch_employee_month(employee_id)

        if not month_data or not month_data.get("weeks"):
            print(f"[DEBUG] Employee {employee_id}: No pending timesheets")
            result["status"] = "empty"
            result["summary"] = "No pending timesheets found."
            return result
        
        print(f"[DEBUG] Employee {employee_id}: Found {len(month_data.get('weeks', []))} weeks")

        # Step 2 — policy engine (detect violations)
        print(f"[DEBUG] Employee {employee_id}: Running policy engine...")
        weekly_reports = run_policy_engine(month_data)
        result["weekly_reports"] = weekly_reports

        # Step 3 — metrics engine
        print(f"[DEBUG] Employee {employee_id}: Computing monthly metrics...")
        monthly_metrics = compute_monthly_metrics(weekly_reports)
        result["monthly_metrics"] = monthly_metrics

        # Step 4 — AGENTIC BATCH DECISION (ONE LLM CALL for all weeks)
        print(f"[DEBUG] Employee {employee_id}: Running BATCH agentic analysis...")
        
        weeks_data = weekly_reports["weeks"]
        
        # Single LLM call analyzes all weeks
        agentic_result = run_batch_agentic_decision(employee_id, weeks_data)
        
        # Extract decisions
        agent_weekly_decisions = agentic_result.get("weekly_decisions", [])
        overall_assessment = agentic_result.get("overall_assessment", {})
        
        # Build weekly decisions with entries
        weekly_decisions = []
        for i, week in enumerate(weeks_data):
            # Match agent decision to this week
            agent_decision = next(
                (d for d in agent_weekly_decisions if d["week"] == week["week_start"]),
                {"decision": "REVIEW", "reason": "No decision from agent"}
            )
            
            weekly_decisions.append({
                "timesheet_id": week.get("timesheet_id"),
                "week_start": week["week_start"],
                "decision": agent_decision["decision"],
                "reason": agent_decision.get("reason", ""),
                "entries": week.get("entries", [])
            })
        
        # Determine overall decision
        review_count = sum(1 for w in weekly_decisions if w["decision"] == "REVIEW")
        
        if review_count > 0:
            overall = {
                "decision": "REVIEW",
                "reason": f"{review_count} week(s) require review"
            }
        else:
            overall = {
                "decision": "APPROVE",
                "reason": None
            }
        
        decisions = {
            "weekly": weekly_decisions,
            "overall": overall,
            "agent_assessment": overall_assessment
        }
        
        result["decisions"] = decisions
        
        # ✅ Generate insightful AI summary with analysis
        pattern = overall_assessment.get("pattern", "Normal behavior")
        risk = overall_assessment.get("risk", "low")
        rec = overall_assessment.get("recommendation", "approve_all")
        
        # Calculate metrics for analysis - COUNT ONLY ACTUAL VIOLATIONS FROM DATA
        total_hours = sum(w.get("metrics", {}).get("total_hours", 0) for w in weeks_data)
        
        # ✅ FIX: Count violations from actual data, not from decisions
        total_violations = 0
        for w in weeks_data:
            actual_violations = w.get("violations", [])
            if actual_violations:
                total_violations += len(actual_violations)
        
        avg_hours = total_hours / len(weeks_data) if weeks_data else 0
        
        print(f"[DEBUG] Employee {employee_id}: Actual violations from data: {total_violations}")
        
        # Get violation types for context - FROM ACTUAL DATA ONLY
        violation_types = []
        for w in weeks_data:
            for v in w.get("violations", []):
                vtype = v.get("type", "")
                if vtype and vtype not in [vt[0] for vt in violation_types]:
                    # Map to readable name
                    readable = {
                        "worked_on_holiday": "holiday work",
                        "leave_without_request": "unapproved leave",
                        "impossible_shift": "excessive hours",
                        "zero_hour_work_entry": "zero hours logged",
                        "no_work_entries": "missing entries"
                    }.get(vtype, vtype.replace("_", " "))
                    violation_types.append((vtype, readable))
        
        # Build analytical summary
        if total_violations == 0:
            if avg_hours < 25:
                summary = f"Employee shows consistent attendance across {len(weeks_data)} weeks but with concerning underutilization (avg {avg_hours:.1f}h/week, below standard 30-40h range). No policy violations detected. Pattern indicates possible capacity issues or workload distribution problems. Recommend discussing workload allocation with employee."
            elif avg_hours > 50:
                summary = f"Employee demonstrates high commitment with {len(weeks_data)} weeks averaging {avg_hours:.1f}h/week (above standard 40h). No policy violations, but sustained overwork may indicate resource constraints or unrealistic deadlines. Consider workload assessment to prevent burnout."
            else:
                summary = f"Employee maintained consistent performance across {len(weeks_data)} weeks, averaging {avg_hours:.1f}h/week within normal range. No policy violations or concerning patterns detected. Demonstrates reliable time management and policy compliance."
        
        elif total_violations == 1:
            violation_desc = violation_types[0][1] if violation_types else "policy issue"
            hours_assessment = "appropriate" if 30 <= avg_hours <= 45 else "noteworthy"
            summary = f"Employee submitted {len(weeks_data)} weeks with single isolated incident ({violation_desc}). Average workload of {avg_hours:.1f}h/week is {hours_assessment}. Pattern suggests anomaly rather than systematic issue, but manager should verify circumstances of the violation."
        
        else:  # 2+ violations
            violation_list = ", ".join([vt[1] for vt in violation_types[:3]])  # First 3 types
            summary = f"Employee shows {total_violations} policy violations across {len(weeks_data)} weeks including {violation_list}. Average {avg_hours:.1f}h/week with recurring compliance issues. Pattern indicates systematic problem requiring immediate manager intervention and corrective discussion. Recommend detailed review of all flagged weeks."
        
        result["summary"] = summary
        
        print(f"[DEBUG] Employee {employee_id}: Pipeline complete - Overall: {overall['decision']}")
        return result

    except Exception as e:
        print(f"[DEBUG] Employee {employee_id}: Pipeline error - {str(e)}")
        import traceback
        traceback.print_exc()
        result["status"] = "error"
        result["error"] = str(e)
        return result