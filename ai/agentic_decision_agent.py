# ai/agentic_decision_agent_optimized.py

"""
OPTIMIZED Agentic Decision Agent
---------------------------------
Fixed issues:
1. Clear, specific reasons with workload considerations
2. Proper risk assessment
3. JSON parsing handles LLM adding text before/after JSON
4. No redundant AI summary
"""

import json
import os
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def extract_json_from_text(text):
    """
    Extract JSON from text that might have explanation before/after
    """
    # Try to find JSON between curly braces
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    return text




def run_batch_agentic_decision(employee_id, weeks_data):
    """
    Analyze ALL weeks for an employee in ONE LLM call
    
    Returns decisions for all weeks + monthly analysis
    """
    
    # Prepare detailed week summaries with context
    week_summaries = []
    for week in weeks_data:
        violations = week.get("violations", [])
        metrics = week.get("metrics", {})
        signals = week.get("signals", {})
        
        # Get actual violation details for better reasoning
        violation_details = []
        for v in violations:
            vtype = v.get("type", "unknown")
            date = v.get("date", "")
            
            # Create descriptive violation
            if vtype == "worked_on_holiday":
                violation_details.append(f"Worked on holiday ({date})")
            elif vtype == "leave_without_request":
                violation_details.append(f"Unapproved leave ({date})")
            elif vtype == "rejected_leave_used":
                violation_details.append(f"Used rejected leave ({date})")
            elif vtype == "fake_holiday_entry":
                violation_details.append(f"Invalid holiday entry ({date})")
            elif vtype == "zero_hour_work_entry":
                violation_details.append(f"Zero hours logged ({date})")
            elif vtype == "impossible_shift":
                hours = v.get("hours", 0)
                violation_details.append(f"Impossible hours: {hours}h ({date})")
            elif vtype == "no_work_entries":
                violation_details.append(f"No work entries for week")
            else:
                violation_details.append(vtype.replace("_", " ").title())
        
        week_summaries.append({
            "week": week.get("week_start"),
            "violations": violation_details,  # Detailed violations
            "total_hours": metrics.get("total_hours", 0),
            "working_days": metrics.get("working_days", 0),
            "avg_hours_per_day": metrics.get("avg_hours", 0),
            "overload_days": len(signals.get("overload_days", [])),
            "underutilized_days": len(signals.get("underutilized_days", []))
        })
    
    prompt = f"""
You are a timesheet approval agent. Analyze these weeks and make STRICT decisions.

WEEKS DATA:
{json.dumps(week_summaries, indent=2)}

DECISION RULES:
1. If violations exist → REVIEW with specific violation as reason
2. If NO violations but total_hours < 25 → REVIEW with reason "Low hours - review required"
3. If NO violations but total_hours > 50 → REVIEW with reason "Excessive hours - review required"
4. If NO violations and 25-50 hours → APPROVE

RISK ASSESSMENT (BE STRICT):
- 0 violations AND 30-45h/week → "consistent performer", risk: "low"
- 0 violations BUT low hours (<25h) → "workload concerns", risk: "medium"
- 0 violations BUT high hours (>50h) → "overwork pattern", risk: "medium"
- 1 violation → "isolated issues", risk: "medium"
- 2+ violations → "recurring problems", risk: "high" (ALWAYS high for 2+)

RECOMMENDATION:
- Low risk → "approve_all"
- Medium risk (workload) → "review_workload"
- Medium risk (1 violation) → "selective_review"
- High risk (2+ violations) → "detailed_review"

OUTPUT (JSON only, no text before or after):
{{
  "weekly_decisions": [
    {{"week": "2026-01-05", "decision": "APPROVE"}},
    {{"week": "2026-01-12", "decision": "REVIEW", "reason": "Low hours - review required"}}
  ],
  "overall_assessment": {{
    "pattern": "consistent performer",
    "risk": "low",
    "recommendation": "approve_all"
  }}
}}
"""
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            # model="llama-3.3-8b-versatile",
            messages=[
                {"role": "system", "content": "You are a strict policy checker. Only flag actual violations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.05,  # Very deterministic
            max_tokens=400
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Debug: Print what we got
        print(f"[AGENTIC AGENT] Raw response for employee {employee_id}:")
        print(f"[AGENTIC AGENT] {result_text[:200]}...")  # First 200 chars
        
        # Check if response is empty
        if not result_text:
            print(f"[AGENTIC AGENT] Empty response for employee {employee_id}, using fallback")
            raise ValueError("Empty response from LLM")
        
        # ✅ FIX: Extract JSON from mixed text response
        # LLM often adds explanation before/after JSON, so we need to extract just the JSON part
        
        # First, try to find JSON block markers
        if "```json" in result_text:
            # Extract content between ```json and ```
            start = result_text.find("```json") + 7
            end = result_text.find("```", start)
            if end > start:
                result_text = result_text[start:end].strip()
        elif "```" in result_text:
            # Generic code block
            start = result_text.find("```") + 3
            end = result_text.find("```", start)
            if end > start:
                result_text = result_text[start:end].strip()
        
        # If no code blocks, try to find JSON by looking for { and }
        if not result_text.startswith("{"):
            # Find first { and last }
            start = result_text.find("{")
            end = result_text.rfind("}")
            if start != -1 and end != -1 and end > start:
                result_text = result_text[start:end+1].strip()
        
        # Remove any remaining markdown or text
        result_text = result_text.replace("```json", "").replace("```", "").strip()
        
        print(f"[AGENTIC AGENT] Extracted JSON for employee {employee_id}:")
        print(f"[AGENTIC AGENT] {result_text[:200]}...")
        
        # Check again after cleaning
        if not result_text or not result_text.startswith("{"):
            print(f"[AGENTIC AGENT] Invalid JSON format after cleaning, using fallback")
            raise ValueError("Could not extract valid JSON from response")
        
        # Try to parse JSON
        try:
            result = json.loads(result_text)
        except json.JSONDecodeError as je:
            print(f"[AGENTIC AGENT] JSON parse error for employee {employee_id}: {je}")
            print(f"[AGENTIC AGENT] Cleaned text was: {result_text[:500]}")
            raise
        
        # Validate we got the expected structure
        if "weekly_decisions" not in result:
            print(f"[AGENTIC AGENT] Missing weekly_decisions in response, using fallback")
            raise ValueError("Invalid response structure")
        
        print(f"[AGENTIC AGENT] Successfully parsed response for employee {employee_id}")
        
        # ✅ ENFORCE STRICT RULES (override LLM if it got it wrong)
        overall_assessment = result.get("overall_assessment", {})
        
        # Count violations for validation
        total_violations = sum(len(w.get("violations", [])) for w in weeks_data)
        total_hours = sum(w.get("metrics", {}).get("total_hours", 0) for w in weeks_data)
        avg_hours = total_hours / len(weeks_data) if weeks_data else 0
        
        # FORCE correct risk level
        if total_violations >= 2:
            # 2+ violations = ALWAYS HIGH (override LLM)
            overall_assessment["risk"] = "high"
            overall_assessment["pattern"] = "Recurring problems"
            overall_assessment["recommendation"] = "detailed_review"
            print(f"[AGENTIC AGENT] Enforced HIGH risk for {total_violations} violations")
        elif total_violations == 1:
            # 1 violation = MEDIUM
            if overall_assessment.get("risk") != "medium":
                overall_assessment["risk"] = "medium"
                overall_assessment["pattern"] = "Isolated issues"
                overall_assessment["recommendation"] = "selective_review"
                print(f"[AGENTIC AGENT] Corrected to MEDIUM risk for 1 violation")
        else:
            # No violations - check hours
            if avg_hours < 25:
                overall_assessment["risk"] = "medium"
                overall_assessment["pattern"] = "Workload concerns"
                overall_assessment["recommendation"] = "review_workload"
            elif avg_hours > 50:
                overall_assessment["risk"] = "medium"
                overall_assessment["pattern"] = "Overwork pattern"
                overall_assessment["recommendation"] = "review_workload"
            elif 30 <= avg_hours <= 45:
                # Normal hours, no violations
                overall_assessment["risk"] = "low"
                overall_assessment["pattern"] = "Consistent performer"
                overall_assessment["recommendation"] = "approve_all"
            else:
                # Slightly off normal but no violations
                overall_assessment["risk"] = "low"
                overall_assessment["pattern"] = "Consistent performer"
                overall_assessment["recommendation"] = "approve_all"
        
        # Update result with corrected assessment
        result["overall_assessment"] = overall_assessment
        
        # Validate and clean up decisions - STRICT ENFORCEMENT
        validated_decisions = []
        for i, week in enumerate(weeks_data):
            week_start = week.get("week_start")
            violations = week.get("violations", [])
            total_hours = week.get("metrics", {}).get("total_hours", 0)
            
            # ✅ CRITICAL: If NO violations in actual data, FORCE APPROVE (ignore LLM)
            if not violations:
                # No violations = MUST be APPROVE
                # Check if hours are problematic (but don't reject, just note)
                if total_hours < 25:
                    # Low hours but no policy violation - still approve but flag
                    validated_decisions.append({
                        "week": week_start,
                        "decision": "REVIEW",
                        "reason": "Low hours"
                    })
                elif total_hours > 50:
                    # High hours but no policy violation - still approve but flag
                    validated_decisions.append({
                        "week": week_start,
                        "decision": "REVIEW", 
                        "reason": "High hours - review recommended"
                    })
                else:
                    # Normal hours, no violations - MUST APPROVE
                    validated_decisions.append({
                        "week": week_start,
                        "decision": "APPROVE"
                    })
                    print(f"[AGENTIC AGENT] Week {week_start}: No violations, {total_hours}h → APPROVE")
            
            else:
                # Has actual violations - use first violation as reason
                v = violations[0]
                vtype = v.get("type", "")
                date = v.get("date", "")
                hours = v.get("hours", "")
                
                reason_map = {
                    "worked_on_holiday": f"Worked on holiday ({date})",
                    "leave_without_request": f"Unapproved leave ({date})",
                    "rejected_leave_used": f"Used rejected leave ({date})",
                    "impossible_shift": f"Impossible hours: {hours}h ({date})" if hours else f"Impossible hours ({date})",
                    "zero_hour_work_entry": f"Zero hours logged ({date})",
                    "no_work_entries": "No work entries",
                    "fake_holiday_entry": f"Invalid holiday ({date})"
                }
                
                reason = reason_map.get(vtype, "Policy violation")
                
                validated_decisions.append({
                    "week": week_start,
                    "decision": "REVIEW",
                    "reason": reason
                })
                print(f"[AGENTIC AGENT] Week {week_start}: Has violations → REVIEW ({reason})")
        
        return {
            "weekly_decisions": validated_decisions,
            "overall_assessment": result.get("overall_assessment", {
                "pattern": "Normal behavior",
                "risk": "low",
                "recommendation": "approve_all"
            })
        }
        
    except Exception as e:
        print(f"[AGENTIC AGENT] Error for employee {employee_id}: {e}")
        print(f"[AGENTIC AGENT] Using rule-based fallback")
        
        # Fallback: pure rule-based
        fallback_decisions = []
        for week in weeks_data:
            violations = week.get("violations", [])
            
            if violations:
                v = violations[0]
                vtype = v.get("type", "")
                date = v.get("date", "")
                
                reason_map = {
                    "worked_on_holiday": f"Worked on holiday ({date})",
                    "leave_without_request": f"Unapproved leave ({date})",
                    "rejected_leave_used": f"Used rejected leave ({date})",
                    "impossible_shift": f"Impossible hours ({date})",
                    "zero_hour_work_entry": f"Zero hours logged ({date})",
                    "no_work_entries": "No work entries",
                    "fake_holiday_entry": f"Invalid holiday ({date})"
                }
                
                reason = reason_map.get(vtype, "Policy violation")
                
                fallback_decisions.append({
                    "week": week.get("week_start"),
                    "decision": "REVIEW",
                    "reason": reason
                })
            else:
                fallback_decisions.append({
                    "week": week.get("week_start"),
                    "decision": "APPROVE"
                })
        
        # Count violations to determine pattern
        total_violations = sum(len(w.get("violations", [])) for w in weeks_data)
        total_hours = sum(w.get("metrics", {}).get("total_hours", 0) for w in weeks_data)
        avg_hours_week = total_hours / len(weeks_data) if weeks_data else 0
        
        # STRICT risk assessment
        if total_violations >= 2:
            pattern = "Recurring problems"
            risk = "high"  # 2+ violations = ALWAYS high
            rec = "detailed_review"
        elif total_violations == 1:
            pattern = "Isolated issues"
            risk = "medium"
            rec = "selective_review"
        elif avg_hours_week < 25:
            pattern = "Workload concerns"
            risk = "medium"
            rec = "review_workload"
        elif avg_hours_week > 50:
            pattern = "Overwork pattern"
            risk = "medium"
            rec = "review_workload"
        else:
            pattern = "Consistent performer"
            risk = "low"
            rec = "approve_all"
        
        return {
            "weekly_decisions": fallback_decisions,
            "overall_assessment": {
                "pattern": pattern,
                "risk": risk,
                "recommendation": rec
            }
        }