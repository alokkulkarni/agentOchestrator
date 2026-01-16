"""
Sample administrative agent for privileged operations.

This module provides administrative functions that require elevated permissions
and human approval. It demonstrates role-based access control and audit logging.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Simulated system state
_SYSTEM_STATE = {
    "services": {
        "orchestrator": {"status": "running", "uptime": "2h 15m", "requests": 152},
        "database": {"status": "running", "uptime": "5d 3h", "connections": 12},
        "cache": {"status": "running", "uptime": "5d 3h", "hit_rate": 0.87},
        "api_gateway": {"status": "running", "uptime": "5d 3h", "requests": 5432},
    },
    "resources": {
        "cpu_usage": 45.2,
        "memory_usage": 62.8,
        "disk_usage": 38.5,
        "network_in": 125.3,
        "network_out": 89.7,
    },
    "users": [
        {"id": 1, "username": "admin", "role": "administrator", "active": True},
        {"id": 2, "username": "john_doe", "role": "user", "active": True},
        {"id": 3, "username": "jane_smith", "role": "user", "active": True},
        {"id": 4, "username": "old_user", "role": "user", "active": False},
    ],
}


def get_system_status(include_details: bool = True) -> Dict[str, Any]:
    """
    Get system status information.

    This is a read-only operation that doesn't require approval.

    Args:
        include_details: Whether to include detailed metrics

    Returns:
        Dictionary with system status information
    """
    logger.info("Admin: Getting system status")

    status = {
        "timestamp": datetime.utcnow().isoformat(),
        "status": "operational",
        "services_count": len(_SYSTEM_STATE["services"]),
        "services": {},
    }

    # Add service statuses
    for service_name, service_info in _SYSTEM_STATE["services"].items():
        status["services"][service_name] = service_info["status"]

    # Add detailed information if requested
    if include_details:
        status["details"] = {
            "services": _SYSTEM_STATE["services"],
            "resources": _SYSTEM_STATE["resources"],
        }

    return {
        "operation": "get_system_status",
        "success": True,
        "data": status,
        "requires_approval": False,
    }


def list_users(
    role: Optional[str] = None,
    active_only: bool = True,
) -> Dict[str, Any]:
    """
    List system users with optional filtering.

    This is a read-only operation that doesn't require approval.

    Args:
        role: Filter by role (e.g., "administrator", "user")
        active_only: Only return active users

    Returns:
        List of users matching the criteria
    """
    logger.info(f"Admin: Listing users (role={role}, active_only={active_only})")

    users = _SYSTEM_STATE["users"]

    # Apply filters
    if active_only:
        users = [u for u in users if u["active"]]

    if role:
        users = [u for u in users if u["role"] == role]

    return {
        "operation": "list_users",
        "success": True,
        "data": {
            "users": users,
            "count": len(users),
            "filters": {
                "role": role,
                "active_only": active_only,
            },
        },
        "requires_approval": False,
    }


def analyze_logs(
    service: str,
    level: str = "INFO",
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Analyze system logs for a service.

    This is a read-only operation that doesn't require approval.

    Args:
        service: Service name to analyze logs for
        level: Log level filter (DEBUG, INFO, WARNING, ERROR)
        limit: Maximum number of log entries to return

    Returns:
        Log analysis results
    """
    logger.info(f"Admin: Analyzing logs for {service} (level={level}, limit={limit})")

    # Mock log data
    mock_logs = [
        {
            "timestamp": "2026-01-05T10:15:23Z",
            "level": "INFO",
            "message": "Service started successfully",
        },
        {
            "timestamp": "2026-01-05T10:16:45Z",
            "level": "INFO",
            "message": "Processing request",
        },
        {
            "timestamp": "2026-01-05T10:17:12Z",
            "level": "WARNING",
            "message": "High memory usage detected",
        },
        {
            "timestamp": "2026-01-05T10:18:30Z",
            "level": "ERROR",
            "message": "Connection timeout to external service",
        },
        {
            "timestamp": "2026-01-05T10:19:05Z",
            "level": "INFO",
            "message": "Request completed successfully",
        },
    ]

    # Filter by level
    if level != "DEBUG":
        level_priority = {"INFO": 1, "WARNING": 2, "ERROR": 3}
        min_priority = level_priority.get(level, 1)
        mock_logs = [
            log for log in mock_logs
            if level_priority.get(log["level"], 1) >= min_priority
        ]

    # Apply limit
    logs = mock_logs[:limit]

    # Calculate statistics
    level_counts = {}
    for log in mock_logs:
        level_counts[log["level"]] = level_counts.get(log["level"], 0) + 1

    return {
        "operation": "analyze_logs",
        "success": True,
        "data": {
            "service": service,
            "logs": logs,
            "count": len(logs),
            "statistics": {
                "total_entries": len(mock_logs),
                "level_distribution": level_counts,
            },
        },
        "requires_approval": False,
    }


def generate_report(
    report_type: str,
    period: str = "daily",
    format: str = "json",
) -> Dict[str, Any]:
    """
    Generate administrative report.

    This is a read-only operation that doesn't require approval.

    Args:
        report_type: Type of report (performance, usage, security)
        period: Report period (hourly, daily, weekly, monthly)
        format: Output format (json, csv, pdf)

    Returns:
        Generated report data
    """
    logger.info(f"Admin: Generating {report_type} report (period={period}, format={format})")

    # Mock report data
    report_data = {
        "performance": {
            "avg_response_time": 125.5,
            "avg_throughput": 450,
            "error_rate": 0.02,
            "uptime": 99.8,
        },
        "usage": {
            "total_requests": 15234,
            "unique_users": 342,
            "peak_concurrent_users": 89,
            "data_processed_gb": 125.3,
        },
        "security": {
            "failed_logins": 12,
            "blocked_ips": 5,
            "suspicious_activities": 2,
            "security_alerts": 0,
        },
    }

    selected_data = report_data.get(report_type, {})

    return {
        "operation": "generate_report",
        "success": True,
        "data": {
            "report_type": report_type,
            "period": period,
            "format": format,
            "generated_at": datetime.utcnow().isoformat(),
            "data": selected_data,
        },
        "requires_approval": False,
    }


# PRIVILEGED OPERATIONS - Require approval
def restart_service(
    service_name: str,
    force: bool = False,
    justification: str = "",
) -> Dict[str, Any]:
    """
    Restart a system service.

    ⚠️ PRIVILEGED OPERATION - Requires human approval.

    Args:
        service_name: Name of the service to restart
        force: Force restart even if service is busy
        justification: Reason for restart (required)

    Returns:
        Result of restart operation
    """
    logger.warning(f"Admin: Restart requested for {service_name} (force={force})")

    if not justification:
        return {
            "operation": "restart_service",
            "success": False,
            "error": "Justification required for restart operation",
            "requires_approval": True,
        }

    # Check if service exists
    if service_name not in _SYSTEM_STATE["services"]:
        return {
            "operation": "restart_service",
            "success": False,
            "error": f"Service '{service_name}' not found",
            "requires_approval": True,
        }

    # Log the operation
    logger.warning(
        f"Service restart initiated: {service_name}\n"
        f"Force: {force}\n"
        f"Justification: {justification}"
    )

    return {
        "operation": "restart_service",
        "success": True,
        "data": {
            "service": service_name,
            "previous_status": _SYSTEM_STATE["services"][service_name]["status"],
            "new_status": "restarting",
            "force": force,
            "justification": justification,
            "initiated_at": datetime.utcnow().isoformat(),
            "estimated_duration": "30-60 seconds",
        },
        "requires_approval": True,
        "approval_required_by": "administrator",
    }


def update_user_permissions(
    user_id: int,
    new_role: str,
    justification: str = "",
) -> Dict[str, Any]:
    """
    Update user role and permissions.

    ⚠️ PRIVILEGED OPERATION - Requires human approval.

    Args:
        user_id: ID of the user to update
        new_role: New role to assign (user, moderator, administrator)
        justification: Reason for permission change (required)

    Returns:
        Result of permission update
    """
    logger.warning(f"Admin: Permission update requested for user {user_id}")

    if not justification:
        return {
            "operation": "update_user_permissions",
            "success": False,
            "error": "Justification required for permission changes",
            "requires_approval": True,
        }

    # Find user
    user = next((u for u in _SYSTEM_STATE["users"] if u["id"] == user_id), None)
    if not user:
        return {
            "operation": "update_user_permissions",
            "success": False,
            "error": f"User with ID {user_id} not found",
            "requires_approval": True,
        }

    # Validate role
    valid_roles = ["user", "moderator", "administrator"]
    if new_role not in valid_roles:
        return {
            "operation": "update_user_permissions",
            "success": False,
            "error": f"Invalid role. Must be one of: {', '.join(valid_roles)}",
            "requires_approval": True,
        }

    logger.warning(
        f"Permission update initiated:\n"
        f"User: {user['username']} (ID: {user_id})\n"
        f"Current role: {user['role']}\n"
        f"New role: {new_role}\n"
        f"Justification: {justification}"
    )

    return {
        "operation": "update_user_permissions",
        "success": True,
        "data": {
            "user_id": user_id,
            "username": user["username"],
            "previous_role": user["role"],
            "new_role": new_role,
            "justification": justification,
            "initiated_at": datetime.utcnow().isoformat(),
        },
        "requires_approval": True,
        "approval_required_by": "administrator",
        "security_notice": "This operation modifies user permissions and requires administrator approval",
    }


def clear_cache(
    cache_type: str = "all",
    justification: str = "",
) -> Dict[str, Any]:
    """
    Clear system cache.

    ⚠️ PRIVILEGED OPERATION - Requires human approval for 'all' cache type.

    Args:
        cache_type: Type of cache to clear (session, query, all)
        justification: Reason for clearing cache

    Returns:
        Result of cache clearing operation
    """
    logger.warning(f"Admin: Cache clear requested (type={cache_type})")

    requires_approval = cache_type == "all"

    if requires_approval and not justification:
        return {
            "operation": "clear_cache",
            "success": False,
            "error": "Justification required for clearing all caches",
            "requires_approval": True,
        }

    logger.warning(
        f"Cache clear initiated:\n"
        f"Cache type: {cache_type}\n"
        f"Justification: {justification or 'Not provided'}"
    )

    # Mock cache sizes
    cache_sizes = {
        "session": "125 MB",
        "query": "340 MB",
        "all": "465 MB",
    }

    return {
        "operation": "clear_cache",
        "success": True,
        "data": {
            "cache_type": cache_type,
            "size_cleared": cache_sizes.get(cache_type, "Unknown"),
            "justification": justification,
            "initiated_at": datetime.utcnow().isoformat(),
        },
        "requires_approval": requires_approval,
        "approval_required_by": "administrator" if requires_approval else None,
    }


# Example usage
if __name__ == "__main__":
    # Test read-only operations (no approval needed)
    print("=" * 60)
    print("Testing Admin Agent - Read-Only Operations")
    print("=" * 60)

    print("\n1. Get System Status:")
    result = get_system_status(include_details=True)
    print(f"   Status: {result['data']['status']}")
    print(f"   Services: {list(result['data']['services'].keys())}")

    print("\n2. List Users:")
    result = list_users(active_only=True)
    print(f"   Active users: {result['data']['count']}")

    print("\n3. Analyze Logs:")
    result = analyze_logs("orchestrator", level="INFO", limit=5)
    print(f"   Log entries: {result['data']['count']}")

    print("\n4. Generate Report:")
    result = generate_report("performance", period="daily")
    print(f"   Report type: {result['data']['report_type']}")

    print("\n" + "=" * 60)
    print("Testing Admin Agent - Privileged Operations")
    print("=" * 60)

    print("\n5. Restart Service (requires approval):")
    result = restart_service(
        "orchestrator",
        force=False,
        justification="High memory usage detected"
    )
    print(f"   Requires approval: {result['requires_approval']}")
    print(f"   Approval by: {result.get('approval_required_by', 'N/A')}")

    print("\n6. Update User Permissions (requires approval):")
    result = update_user_permissions(
        user_id=2,
        new_role="moderator",
        justification="User demonstrated expertise and reliability"
    )
    print(f"   Requires approval: {result['requires_approval']}")
    print(f"   Previous role: {result['data']['previous_role']}")
    print(f"   New role: {result['data']['new_role']}")

    print("\n7. Clear Cache:")
    result = clear_cache(cache_type="session", justification="")
    print(f"   Requires approval: {result['requires_approval']}")
    print(f"   Size cleared: {result['data']['size_cleared']}")

    print("\n" + "=" * 60)
