"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role = postgresql.ENUM("admin", "engineer", "viewer", name="user_role", create_type=False)
service_status = postgresql.ENUM(
    "healthy", "degraded", "unhealthy", "unknown", name="service_status", create_type=False
)
severity = postgresql.ENUM(
    "critical", "high", "medium", "low", "info", name="severity", create_type=False
)
incident_status = postgresql.ENUM(
    "open",
    "investigating",
    "mitigating",
    "resolved",
    "closed",
    name="incident_status",
    create_type=False,
)
investigation_status = postgresql.ENUM(
    "pending",
    "initializing",
    "gathering_context",
    "log_investigation",
    "metrics_investigation",
    "trace_investigation",
    "deployment_investigation",
    "root_cause_analysis",
    "evidence_evaluation",
    "remediation_proposal",
    "awaiting_approval",
    "completed",
    "failed",
    "cancelled",
    "timed_out",
    name="investigation_status",
    create_type=False,
)
remediation_status = postgresql.ENUM(
    "proposed",
    "approved",
    "rejected",
    "cancelled",
    "executing",
    "succeeded",
    "failed",
    "rolled_back",
    name="remediation_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (
        postgresql.ENUM("admin", "engineer", "viewer", name="user_role"),
        postgresql.ENUM("healthy", "degraded", "unhealthy", "unknown", name="service_status"),
        postgresql.ENUM("critical", "high", "medium", "low", "info", name="severity"),
        postgresql.ENUM(
            "open", "investigating", "mitigating", "resolved", "closed", name="incident_status"
        ),
        postgresql.ENUM(
            "pending",
            "initializing",
            "gathering_context",
            "log_investigation",
            "metrics_investigation",
            "trace_investigation",
            "deployment_investigation",
            "root_cause_analysis",
            "evidence_evaluation",
            "remediation_proposal",
            "awaiting_approval",
            "completed",
            "failed",
            "cancelled",
            "timed_out",
            name="investigation_status",
        ),
        postgresql.ENUM(
            "proposed",
            "approved",
            "rejected",
            "cancelled",
            "executing",
            "succeeded",
            "failed",
            "rolled_back",
            name="remediation_status",
        ),
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("environment", sa.String(64), nullable=False),
        sa.Column("base_url", sa.String(512), nullable=True),
        sa.Column("status", service_status, nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_services_name", "services", ["name"], unique=True)

    op.create_table(
        "service_dependencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_service_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("services.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_service_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("services.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dependency_type", sa.String(64), nullable=False),
        sa.UniqueConstraint("source_service_id", "target_service_id", "dependency_type", name="uq_service_dep"),
    )

    op.create_table(
        "deployments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("services.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.String(128), nullable=False),
        sa.Column("commit_sha", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_deployments_service_id", "deployments", ["service_id"])

    op.create_table(
        "telemetry_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("service_name", sa.String(128), nullable=False),
        sa.Column("environment", sa.String(64), nullable=False),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("trace_id", sa.String(64), nullable=True),
        sa.Column("span_id", sa.String(32), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("attributes", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("raw", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_telemetry_logs_ts", "telemetry_logs", ["timestamp"])
    op.create_index("ix_telemetry_logs_service_ts", "telemetry_logs", ["service_name", "timestamp"])
    op.create_index("ix_telemetry_logs_trace", "telemetry_logs", ["trace_id"])
    op.create_index("ix_telemetry_logs_corr", "telemetry_logs", ["correlation_id"])

    op.create_table(
        "metric_samples",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("service_name", sa.String(128), nullable=False),
        sa.Column("metric_name", sa.String(128), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("labels", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index(
        "ix_metric_samples_service_name_ts",
        "metric_samples",
        ["service_name", "metric_name", "timestamp"],
    )

    op.create_table(
        "telemetry_traces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("service_name", sa.String(128), nullable=False),
        sa.Column("root_operation", sa.String(255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("attributes", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_telemetry_traces_trace_id", "telemetry_traces", ["trace_id"], unique=True)

    op.create_table(
        "telemetry_spans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trace_pk", postgresql.UUID(as_uuid=True), sa.ForeignKey("telemetry_traces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("span_id", sa.String(32), nullable=False),
        sa.Column("parent_span_id", sa.String(32), nullable=True),
        sa.Column("service_name", sa.String(128), nullable=False),
        sa.Column("operation_name", sa.String(255), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("attributes", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_spans_trace", "telemetry_spans", ["trace_id"])

    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("status", incident_status, nullable=False),
        sa.Column("severity", severity, nullable=False),
        sa.Column("service_names", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mttr_seconds", sa.Integer(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index("ix_incidents_severity", "incidents", ["severity"])

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rule_id", sa.String(128), nullable=False),
        sa.Column("service_name", sa.String(128), nullable=False),
        sa.Column("severity", severity, nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("fingerprint", sa.String(128), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("labels", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("annotations", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_alerts_rule_id", "alerts", ["rule_id"])
    op.create_index("ix_alerts_service_name", "alerts", ["service_name"])
    op.create_index("ix_alerts_fingerprint", "alerts", ["fingerprint"])
    op.create_index("ix_alerts_status", "alerts", ["status"])
    op.create_index("ix_alerts_incident_id", "alerts", ["incident_id"])

    op.create_table(
        "investigations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", investigation_status, nullable=False),
        sa.Column("current_step", sa.String(64), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("prompt_version", sa.String(64), nullable=False),
        sa.Column("state", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("rca", postgresql.JSONB(), nullable=True),
        sa.Column("token_usage", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("estimated_cost_usd", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_investigations_incident_id", "investigations", ["incident_id"])
    op.create_index("ix_investigations_status", "investigations", ["status"])

    op.create_table(
        "investigation_checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step", sa.String(64), nullable=False),
        sa.Column("state", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_investigation_checkpoints_investigation_id", "investigation_checkpoints", ["investigation_id"])

    op.create_table(
        "agent_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_name", sa.String(64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("evidence_refs", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_agent_findings_investigation_id", "agent_findings", ["investigation_id"])

    op.create_table(
        "hypotheses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("confidence_components", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("evidence_refs", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("grounded", sa.Boolean(), nullable=True),
        sa.Column("evaluation_notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_hypotheses_investigation_id", "hypotheses", ["investigation_id"])

    op.create_table(
        "remediation_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", remediation_status, nullable=False),
        sa.Column("problem_summary", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("actions", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("risks", sa.Text(), nullable=False),
        sa.Column("rollback_steps", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("expected_impact", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_remediation_plans_investigation_id", "remediation_plans", ["investigation_id"])
    op.create_index("ix_remediation_plans_incident_id", "remediation_plans", ["incident_id"])
    op.create_index("ix_remediation_plans_status", "remediation_plans", ["status"])

    op.create_table(
        "remediation_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("remediation_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("approver_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_remediation_approvals_plan_id", "remediation_approvals", ["plan_id"])

    op.create_table(
        "remediation_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("remediation_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("rollback_status", sa.String(32), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_remediation_executions_plan_id", "remediation_executions", ["plan_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_audit_events_actor_user_id", "audit_events", ["actor_user_id"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])


def downgrade() -> None:
    for table in [
        "audit_events",
        "remediation_executions",
        "remediation_approvals",
        "remediation_plans",
        "hypotheses",
        "agent_findings",
        "investigation_checkpoints",
        "investigations",
        "alerts",
        "incidents",
        "telemetry_spans",
        "telemetry_traces",
        "metric_samples",
        "telemetry_logs",
        "deployments",
        "service_dependencies",
        "services",
        "users",
    ]:
        op.drop_table(table)

    bind = op.get_bind()
    for name in (
        "remediation_status",
        "investigation_status",
        "incident_status",
        "severity",
        "service_status",
        "user_role",
    ):
        postgresql.ENUM(name=name).drop(bind, checkfirst=True)
