export type Role = "admin" | "engineer" | "viewer";
export type Severity = "critical" | "high" | "medium" | "low" | "info";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
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

export interface Service {
  id: string;
  name: string;
  display_name: string;
  status: string;
  environment: string;
  base_url?: string | null;
}

export interface Incident {
  id: string;
  title: string;
  status: string;
  severity: Severity;
  service_names: string[];
  started_at?: string | null;
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

export interface Investigation {
  id: string;
  incident_id: string;
  status: string;
  current_step: string;
  provider: string;
  model: string;
  prompt_version: string;
  rca?: Record<string, unknown> | null;
  token_usage?: Record<string, unknown>;
  estimated_cost_usd?: number;
  started_at: string;
  completed_at?: string | null;
  error_message?: string | null;
}

export interface RemediationPlan {
  id: string;
  investigation_id: string;
  incident_id: string;
  status: string;
  problem_summary: string;
  rationale: string;
  actions: Array<Record<string, unknown>>;
  risks: string;
  rollback_steps: unknown[];
  expected_impact: string;
  created_at: string;
}

export interface EvaluationRun {
  id: string;
  dataset_version: string;
  provider: string;
  model: string;
  prompt_version: string;
  status: string;
  metrics?: Record<string, unknown> | null;
  created_at: string;
  completed_at?: string | null;
}
