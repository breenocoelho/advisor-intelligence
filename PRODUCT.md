# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Two roles are equally central today, both at investment-advisory firms and independent practices in Brazil:

- **Advisor (`advisor`)**: an individual assessor de investimentos who works their own client book daily — checks what needs attention today, drills into a client's positions and history, and acts on alerts/tasks.
- **Admin (`admin`)**: manages integrations and sees across all clients/advisors in the organization — office-level oversight, not just a single book.

Both are professionals inside a wealth-management or independent-advisory business, not the end retail investor.

## Product Purpose

Advisor Intelligence is a B2B intelligence layer for investment advisors and wealth-management offices. It does not replace the CRM, brokerage, consolidator, or custodian — it consumes their data, normalizes it into its own canonical model, and surfaces prioritized, explainable alerts and insights. Success means an advisor opens the product and immediately knows what deserves attention today and why, instead of having to piece that together from fragmented source systems.

## Positioning

"Não mostre ao assessor o que está acontecendo. Diga o que merece atenção e por quê." The product's mechanism a neighboring tool can't truthfully copy: it doesn't just display positions/data (that's the custodian's/CRM's job) — it runs an explainable rules engine over normalized multi-account data to generate prioritized, reasoned alerts and insights, with full traceability back to the source data.

## Operating Context

- Data pipeline: scheduled sync (Celery Beat) pulls client/account/position data from source systems, maps it into the canonical model, upserts it, then the rules/insights engine runs and produces alerts.
- Current source integration: XP only. Access requires formal partner accreditation with XP (commercial/legal process, not self-serve), which has not been completed yet — this is the primary schedule risk for going live with real data.
- **All data in the product today is synthetic** (generated via `backend/generate_xp_mocks.py` into `backend/mocks/`, loaded via `backend/sync_xp_mock.py` / `backend/replay_xp_mock_history.py`). No real client or position data is in use. Design and copy must not imply live XP connectivity or real client outcomes until this changes.
- Multi-tenant via Clerk Organizations; isolation enforced by `org_id` filtering in the application layer (no Postgres RLS yet).
- Surfaces already implemented beyond the original MVP alert engine, treated as stable product surfaces (not throwaway prototypes): Today dashboard, alert list, per-client view with client-scoped alerts, an Insights surface, a Tasks ("Tarefas") surface, and a Config/Thresholds surface for tuning alert rule parameters. This is a deliberate scope expansion beyond the original MVP document, still being validated with the same pilot motion.
- Backend JWT validation for Clerk is not yet implemented — the API currently accepts requests without real auth enforcement. Do not treat authenticated-only claims as true in this state.

## Capabilities and Constraints

- Alert types live in the rules engine: caixa ociosa (idle cash), concentração (concentration), movimentação relevante (relevant movement), vencimento próximo (upcoming maturity) — each with configurable thresholds now exposed via the Config/Thresholds surface.
- Insights and position history are generated from the same canonical, XP-sourced (currently mocked) data — not from a separate data source.
- Alert severities: `critical`, `opportunity`, `follow_up`.
- No CRM, suitability, or propensity/opportunity scoring in the product yet — explicitly deferred until after traction from XP-connected pilots.
- No AI/Copilot layer yet; any future natural-language layer is planned to sit behind a structured query/intelligence layer, never with direct LLM access to the database.
- Stack (existing, not a greenfield decision): Next.js/React/TypeScript frontend (Tailwind v4), FastAPI/Python backend, PostgreSQL via SQLAlchemy+Alembic, Celery+Redis for jobs, Clerk for auth/multi-tenancy, Railway (backend) + Vercel (frontend) hosting.
- Language: Portuguese (pt-BR) is the product's working language — labels, dates, and copy are pt-BR throughout.

## Brand Commitments

Product name: "Advisor Intelligence." No other binding brand assets, logo, or voice guidelines have been confirmed beyond the name itself.

## Evidence on Hand

No real client data, testimonials, pilot results, or case studies exist yet — everything currently rendered in the product is generated synthetic (mock) data standing in for XP data ahead of accreditation. Future design and copy work must not fabricate real client outcomes, logos, or metrics.

## Product Principles

- Prioritize and explain, never just display — every alert/insight must be traceable to why it fired, not just that it fired.
- Layer, don't replace — the product sits on top of custodians/CRMs/consolidators and must never present itself as a system of record for data it doesn't own.
- Simplicity → reliability → explainability → extensibility → scalability, in that order, for every engineering and design decision.
- Multi-tenant isolation (org_id) and role separation (advisor vs. admin) are load-bearing, not cosmetic — advisor views are scoped to their own book, admin views span the org.
- Don't imply capabilities or data connectivity (live XP data, AI copilot, propensity scoring) that don't exist yet.
