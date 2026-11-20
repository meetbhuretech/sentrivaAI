import uuid
from datetime import datetime
from decimal import Decimal

from sentinelai_contracts import InvestigationStatus
from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[InvestigationStatus] = mapped_column(
        Enum(
            InvestigationStatus,
            name="investigation_status",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=InvestigationStatus.PENDING,
        nullable=False,
        index=True,
    )
    current_step: Mapped[str] = mapped_column(String(64), default="pending", nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), default="v1", nullable=False)
    state: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    rca: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    token_usage: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    estimated_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), default=Decimal("0"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class InvestigationCheckpoint(Base):
    __tablename__ = "investigation_checkpoints"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AgentFinding(Base):
    __tablename__ = "agent_findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    evidence_refs: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="deterministic", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Hypothesis(Base):
    __tablename__ = "hypotheses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    rank: Mapped[int] = mapped_column(nullable=False, default=1)
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    confidence_components: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    evidence_refs: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    grounded: Mapped[bool | None] = mapped_column(nullable=True)
    evaluation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
