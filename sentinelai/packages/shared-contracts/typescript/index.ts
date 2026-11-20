/** Shared SENTINELAI TypeScript contracts — keep aligned with OpenAPI. */

export type Role = "admin" | "engineer" | "viewer";
export type Severity = "critical" | "high" | "medium" | "low" | "info";
export type IncidentStatus =
  | "open"
  | "investigating"
  | "mitigating"
  | "resolved"
  | "closed";
export type ServiceStatus = "healthy" | "degraded" | "unhealthy" | "unknown";

export type InvestigationStatus =
  | "pending"
  | "initializing"
  | "gathering_context"
  | "log_investigation"
  | "metrics_investigation"
  | "trace_investigation"
  | "deployment_investigation"
  | "root_cause_analysis"
  | "evidence_evaluation"
  | "remediation_proposal"
  | "awaiting_approval"
  | "completed"
  | "failed"
  | "cancelled"
  | "timed_out";

export type RemediationStatus =
  | "proposed"
  | "approved"
  | "rejected"
  | "cancelled"
  | "executing"
  | "succeeded"
  | "failed"
  | "rolled_back";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Service {
  id: string;
  name: string;
  display_name: string;
  status: ServiceStatus;
  environment: string;
  base_url?: string;
}

export interface OverviewResponse {
  total_services: number;
  healthy_services: number;
  active_incidents: number;
  severity_distribution: Record<string, number>;
  request_rate: number;
  error_rate: number;
  latency: { p50_ms: number; p95_ms: number; p99_ms: number };
  resource_utilization: { cpu_percent: number; memory_percent: number };
  mttr_seconds: number | null;
  ai_investigations: { active: number; completed: number; failed: number };
  generated_at?: string;
}

export interface Incident {
  id: string;
  title: string;
  status: IncidentStatus;
  severity: Severity;
  service_names: string[];
  started_at?: string;
  detected_at: string;
  resolved_at?: string | null;
  mttr_seconds?: number | null;
  summary?: string | null;
}

export interface Paginated<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export const REMEDIATION_ACTION_ALLOWLIST = [
  "restart_service",
  "clear_redis_connections",
  "scale_connection_pool",
  "rollback_deployment",
  "disable_scenario",
  "flush_cache_namespace",
] as const;
