# ui/mock_data.py - FULLY FIXED VERSION
def get_mock_manager_result(manager_id=None):
    return {
        "status": "ok",
        "error": None,
        "manager_id": manager_id or 123,
        "team_summary": {
            "total_employees": 3,
            "needs_review": 1,
            "clean": 2,
            "pipeline_errors": 0
        },
        "employees": [
            {
                "status": "ok",  # ✅ FIXED: Added status
                "employee_id": 8,
                "employee_code": "EMP008",
                "employee_name": "Arjun Kumar",
                "summary": "Workload stable across the month. One isolated holiday work entry requires review.",
                "decisions": {
                    "weekly": [
                        {
                            "week_start": "2026-01-05", 
                            "decision": "APPROVE",
                            "entries": [
                                {"date": "2026-01-05", "type": "WORK", "hours": 7.7},
                                {"date": "2026-01-06", "type": "WORK", "hours": 7.6},
                                {"date": "2026-01-07", "type": "WORK", "hours": 8.3},
                                {"date": "2026-01-08", "type": "WORK", "hours": 8.3},
                                {"date": "2026-01-09", "type": "WORK", "hours": 7.5}
                            ]
                        },
                        {
                            "week_start": "2026-01-12", 
                            "decision": "APPROVE",
                            "entries": [
                                {"date": "2026-01-12", "type": "WORK", "hours": 8.0},
                                {"date": "2026-01-13", "type": "WORK", "hours": 7.8},
                                {"date": "2026-01-14", "type": "WORK", "hours": 8.2},
                                {"date": "2026-01-15", "type": "WORK", "hours": 7.9},
                                {"date": "2026-01-16", "type": "WORK", "hours": 8.1}
                            ]
                        },
                        {
                            "week_start": "2026-01-19", 
                            "decision": "APPROVE",
                            "entries": [
                                {"date": "2026-01-19", "type": "WORK", "hours": 7.9},
                                {"date": "2026-01-20", "type": "WORK", "hours": 8.0},
                                {"date": "2026-01-21", "type": "WORK", "hours": 7.7},
                                {"date": "2026-01-22", "type": "WORK", "hours": 8.4},
                                {"date": "2026-01-23", "type": "WORK", "hours": 7.6}
                            ]
                        },
                        {
                            "week_start": "2026-01-26",
                            "decision": "REVIEW",
                            "reason": "Work recorded on holiday (2026-01-26)",
                            "entries": [
                                {"date": "2026-01-26", "type": "WORK", "hours": 6.5},  # Holiday work
                                {"date": "2026-01-27", "type": "WORK", "hours": 8.0},
                                {"date": "2026-01-28", "type": "WORK", "hours": 7.8},
                                {"date": "2026-01-29", "type": "WORK", "hours": 8.2},
                                {"date": "2026-01-30", "type": "WORK", "hours": 7.9}
                            ]
                        }
                    ],
                    "overall": {
                        "decision": "REVIEW",
                        "reason": "1 week(s) require review: Work recorded on holiday (2026-01-26)"
                    }
                }
            },
            {
                "status": "ok",  # ✅ FIXED: Added status
                "employee_id": 9,
                "employee_code": "EMP009",
                "employee_name": "Meera Nair",
                "summary": "Consistent reporting across all weeks. No policy violations detected. Stable workload.",
                "decisions": {
                    "weekly": [
                        {"week_start": "2026-01-05", "decision": "APPROVE", "entries": [
                            {"date": "2026-01-05", "type": "WORK", "hours": 7.7},
                            {"date": "2026-01-06", "type": "WORK", "hours": 7.6},
                            {"date": "2026-01-07", "type": "WORK", "hours": 8.3},
                            {"date": "2026-01-08", "type": "WORK", "hours": 8.3},
                            {"date": "2026-01-09", "type": "WORK", "hours": 7.5}
                        ]},
                        {"week_start": "2026-01-12", "decision": "APPROVE", "entries": [
                            {"date": "2026-01-12", "type": "WORK", "hours": 8.0},
                            {"date": "2026-01-13", "type": "WORK", "hours": 7.8},
                            {"date": "2026-01-14", "type": "WORK", "hours": 8.2},
                            {"date": "2026-01-15", "type": "WORK", "hours": 7.9},
                            {"date": "2026-01-16", "type": "WORK", "hours": 8.1}
                        ]},
                        {"week_start": "2026-01-19", "decision": "APPROVE", "entries": [
                            {"date": "2026-01-19", "type": "WORK", "hours": 7.9},
                            {"date": "2026-01-20", "type": "WORK", "hours": 8.0},
                            {"date": "2026-01-21", "type": "WORK", "hours": 7.7},
                            {"date": "2026-01-22", "type": "WORK", "hours": 8.4},
                            {"date": "2026-01-23", "type": "WORK", "hours": 7.6}
                        ]},
                        {"week_start": "2026-01-26", "decision": "APPROVE", "entries": [
                            {"date": "2026-01-26", "type": "WORK", "hours": 7.8},
                            {"date": "2026-01-27", "type": "WORK", "hours": 8.0},
                            {"date": "2026-01-28", "type": "WORK", "hours": 7.9},
                            {"date": "2026-01-29", "type": "WORK", "hours": 8.1},
                            {"date": "2026-01-30", "type": "WORK", "hours": 7.7}
                        ]}
                    ],
                    "overall": {"decision": "APPROVE"}
                }
            },
            {
                "status": "ok",  # ✅ 3rd employee
                "employee_id": 10,
                "employee_code": "EMP010",
                "employee_name": "Rahul Patel",
                "summary": "Multiple 12+ hour shifts detected. Workload management discussion recommended.",
                "decisions": {
                    "weekly": [
                        {"week_start": "2026-01-05", "decision": "APPROVE", "entries": [...]},
                        {"week_start": "2026-01-12", "decision": "REVIEW", "reason": "Impossible shift hours (12.5h on 2026-01-13)", "entries": [...]},
                        {"week_start": "2026-01-19", "decision": "APPROVE", "entries": [...]},
                        {"week_start": "2026-01-26", "decision": "APPROVE", "entries": [...]}
                    ],
                    "overall": {"decision": "REVIEW", "reason": "1 week(s) require review"}
                }
            }
        ]
    }
