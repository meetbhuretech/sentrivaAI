# SENTINELAI Threat Model (v0.1)

## Assets

- User credentials and JWTs
- Telemetry (logs may contain sensitive fields)
- Investigation / RCA artifacts
- Remediation plans and approval records
- AI API keys
- Audit trail integrity

## Trust Boundaries

1. Browser → API (JWT, CORS allowlist)
2. Simulator → API ingest (internal token)
3. API → LLM providers (untrusted external)
4. API → MCP tools (scoped permissions)
5. Remediation sandbox → simulator only (never real prod by default)

## Key Threats & Mitigations

| Threat | Mitigation |
|--------|------------|
| Credential stuffing / weak passwords | bcrypt hashing; rate limits; min password length |
| Privilege escalation | RBAC with role rank checks on every mutating route |
| Prompt injection via logs | Logs/tool results framed as untrusted data; no instruction following from telemetry |
| Arbitrary command execution | Allowlisted remediation actions only; never exec LLM shell |
| Secret leakage in logs | Redaction middleware before persist/LLM context |
| CSRF / CORS abuse | Explicit CORS origins; JWT bearer (not cookie-primary) |
| Replay / stale tokens | Short-lived access tokens + refresh rotation |
| Evaluation score fabrication | Scores only written by evaluation runner from measured results |
| Supply-chain / dependency risk | Pinned versions; CI vulnerability scan (Milestone 10) |

## Roles

| Role | Capabilities |
|------|--------------|
| viewer | Read dashboards, telemetry, investigations |
| engineer | + trigger scenarios, investigations, approve/reject remediation |
| admin | + user management, settings, audit access |

## Explicit Non-Claims

- This demo stack is not hardened for internet-facing production without additional controls (WAF, IdP, secrets manager, network policies).
- Sandbox remediation is intentionally limited to the local simulator.
