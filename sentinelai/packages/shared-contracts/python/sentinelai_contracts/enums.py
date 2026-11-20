from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    ENGINEER = "engineer"
    VIEWER = "viewer"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IncidentStatus(StrEnum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


class InvestigationStatus(StrEnum):
    PENDING = "pending"
    INITIALIZING = "initializing"
    GATHERING_CONTEXT = "gathering_context"
    LOG_INVESTIGATION = "log_investigation"
    METRICS_INVESTIGATION = "metrics_investigation"
    TRACE_INVESTIGATION = "trace_investigation"
    DEPLOYMENT_INVESTIGATION = "deployment_investigation"
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"
    EVIDENCE_EVALUATION = "evidence_evaluation"
    REMEDIATION_PROPOSAL = "remediation_proposal"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class RemediationStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ServiceStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class EvidenceKind(StrEnum):
    LOG = "log"
    METRIC = "metric"
    SPAN = "span"
    TRACE = "trace"
    DEPLOYMENT = "deployment"
    ALERT = "alert"


class AnalysisSource(StrEnum):
    LLM = "llm"
    DETERMINISTIC = "deterministic"
    HYBRID = "hybrid"


# Allowlisted remediation action types — never execute arbitrary LLM shell.
REMEDIATION_ACTION_ALLOWLIST = frozenset(
    {
        "restart_service",
        "clear_redis_connections",
        "scale_connection_pool",
        "rollback_deployment",
        "disable_scenario",
        "flush_cache_namespace",
    }
)

ROLE_RANK = {
    Role.VIEWER: 1,
    Role.ENGINEER: 2,
    Role.ADMIN: 3,
}
