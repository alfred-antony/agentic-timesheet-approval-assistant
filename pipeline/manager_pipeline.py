# pipeline/manager_pipeline.py

from pipeline.employee_pipeline import run_employee_pipeline
from data.data_agent import fetch_employees_under_manager


def run_manager_pipeline_with_progress(manager_id):
    """
    Generator that yields progress updates as employees are processed.
    
    Yields:
        dict: Progress update with current employee info and results
    """
    
    try:
        employees = fetch_employees_under_manager(manager_id)
        total = len(employees)
        
        if total == 0:
            yield {
                "type": "complete",
                "employees": [],
                "team_summary": {
                    "total_employees": 0,
                    "needs_review": 0,
                    "clean": 0,
                    "pipeline_errors": 0
                }
            }
            return
        
        review_count = 0
        clean_count = 0
        error_count = 0
        all_results = []
        
        for idx, emp in enumerate(employees, 1):
            # Yield progress before processing
            yield {
                "type": "progress",
                "current": idx,
                "total": total,
                "employee_name": emp.get("employee_name", "Unknown"),
                "status": "processing"
            }
            
            # Process employee
            try:
                employee_result = run_employee_pipeline(emp["employee_id"])
                employee_result["employee_code"] = emp.get("employee_code", "N/A")
                employee_result["employee_name"] = emp.get("employee_name", "Unknown")
                all_results.append(employee_result)
                
                # Track stats
                if employee_result["status"] == "error":
                    error_count += 1
                elif employee_result["status"] == "ok":
                    overall = employee_result.get("decisions", {}).get("overall", {}).get("decision", "REVIEW")
                    if overall == "REVIEW":
                        review_count += 1
                    else:
                        clean_count += 1
                
                # Yield completion for this employee
                yield {
                    "type": "employee_complete",
                    "current": idx,
                    "total": total,
                    "employee_name": emp.get("employee_name", "Unknown"),
                    "result": employee_result
                }
                
            except Exception as e:
                # Handle individual employee errors
                error_result = {
                    "employee_id": emp["employee_id"],
                    "employee_code": emp.get("employee_code", "N/A"),
                    "employee_name": emp.get("employee_name", "Unknown"),
                    "status": "error",
                    "error": str(e),
                    "weekly_reports": [],
                    "monthly_metrics": None,
                    "summary": None,
                    "decisions": None
                }
                all_results.append(error_result)
                error_count += 1
                
                yield {
                    "type": "employee_complete",
                    "current": idx,
                    "total": total,
                    "employee_name": emp.get("employee_name", "Unknown"),
                    "result": error_result
                }
        
        # Yield final summary
        yield {
            "type": "complete",
            "employees": all_results,
            "team_summary": {
                "total_employees": total,
                "needs_review": review_count,
                "clean": clean_count,
                "pipeline_errors": error_count
            }
        }
        
    except Exception as e:
        # Handle fatal errors
        yield {
            "type": "error",
            "error": str(e),
            "employees": [],
            "team_summary": {
                "total_employees": 0,
                "needs_review": 0,
                "clean": 0,
                "pipeline_errors": 1
            }
        }


def run_manager_pipeline(manager_id):
    """
    Standard pipeline (non-generator) for backwards compatibility
    """
    
    result = {
        "manager_id": manager_id,
        "employees": [],
        "team_summary": {},
        "status": "ok",
        "error": None
    }

    try:
        print(f"[DEBUG] Fetching employees for manager {manager_id}")
        employees = fetch_employees_under_manager(manager_id)
        
        if not employees:
            print(f"[DEBUG] No employees found for manager {manager_id}")
            result["team_summary"] = {
                "total_employees": 0,
                "needs_review": 0,
                "clean": 0,
                "pipeline_errors": 0
            }
            return result
        
        print(f"[DEBUG] Found {len(employees)} employees")

        review_count = 0
        clean_count = 0
        error_count = 0

        for emp in employees:
            print(f"[DEBUG] Processing employee {emp.get('employee_name', 'Unknown')} (ID: {emp.get('employee_id')})")
            
            try:
                employee_result = run_employee_pipeline(emp["employee_id"])
                
                if not employee_result:
                    print(f"[DEBUG] Employee pipeline returned None for {emp['employee_id']}")
                    employee_result = {
                        "employee_id": emp["employee_id"],
                        "status": "error",
                        "error": "Pipeline returned None",
                        "weekly_reports": [],
                        "monthly_metrics": None,
                        "summary": None,
                        "decisions": None
                    }
                
                employee_result["employee_code"] = emp.get("employee_code", "N/A")
                employee_result["employee_name"] = emp.get("employee_name", "Unknown")
                result["employees"].append(employee_result)

                if employee_result.get("status") == "error":
                    error_count += 1
                    print(f"[DEBUG] Employee {emp['employee_id']} status=error: {employee_result.get('error')}")
                    continue

                decisions = employee_result.get("decisions")
                if not decisions:
                    print(f"[DEBUG] No decisions for employee {emp['employee_id']}")
                    error_count += 1
                    continue
                
                overall_decision = decisions.get("overall", {})
                if not overall_decision:
                    print(f"[DEBUG] No overall decision for employee {emp['employee_id']}")
                    error_count += 1
                    continue
                
                overall = overall_decision.get("decision", "REVIEW")
                print(f"[DEBUG] Employee {emp['employee_id']} decision: {overall}")

                if overall == "REVIEW":
                    review_count += 1
                else:
                    clean_count += 1
                    
            except Exception as emp_error:
                print(f"[DEBUG] Exception processing employee {emp.get('employee_id')}: {str(emp_error)}")
                import traceback
                traceback.print_exc()
                result["employees"].append({
                    "employee_id": emp.get("employee_id", "unknown"),
                    "employee_code": emp.get("employee_code", "N/A"),
                    "employee_name": emp.get("employee_name", "Unknown"),
                    "status": "error",
                    "error": str(emp_error),
                    "weekly_reports": [],
                    "monthly_metrics": None,
                    "summary": None,
                    "decisions": None
                })
                error_count += 1

        result["team_summary"] = {
            "total_employees": len(employees),
            "needs_review": review_count,
            "clean": clean_count,
            "pipeline_errors": error_count
        }
        
        print(f"[DEBUG] Pipeline complete: {result['team_summary']}")
        return result

    except Exception as e:
        print(f"[DEBUG] Fatal pipeline error: {str(e)}")
        import traceback
        traceback.print_exc()
        result["status"] = "error"
        result["error"] = str(e)
        return result