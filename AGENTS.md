PART A — Save this as AGENTS.md at your project root

Antigravity (and most modern agentic tools) automatically reads AGENTS.md before starting any task. This is where your non-negotiables live so you never have to repeat them.

markdown
# AGENTS.md — CartMind

## Project
CartMind — an AI upsell/cross-sell agent with conversational checkout, built for
the Razorpay AI Buildathon 2026 (Track 01: AI Growth & Agentic Commerce).
Full specs live in /PRD.md and /TRD.md at the repo root — read both before
planning any non-trivial task.

## Stack (do not substitute without asking)
- Frontend: React + Vite + Tailwind CSS
- Backend: FastAPI (Python 3.11+)
- LLM: Groq API, model "llama-3.3-70b-versatile", using function/tool calling
- Payments: razorpay Python SDK, TEST MODE ONLY
- Database: SQLite via SQLModel

## Non-negotiable architecture rule
The LLM reasoning layer must NEVER call the Razorpay API or directly mutate
cart/order state. It may only emit structured tool calls (recommend_product,
apply_discount, initiate_checkout) as defined in TRD.md §6. A separate,
pure-Python, deterministic Gating Engine validates every tool call before
anything executes. If you are about to write code where an LLM response
flows directly into a Razorpay call or a database write with no gate in
between, stop and flag it instead of proceeding.

## Audit logging rule
Every proposed action AND every gate decision (approved / blocked / modified)
must be written to the audit_log / gate_decisions tables, including a
human-readable reason string. Blocked actions are not silently dropped.

## Coding standards
- Python: type hints on all function signatures, PEP 8, docstrings on public
  functions.
- React: functional components + hooks only, no class components.
- Styling: Tailwind utility classes only — no inline styles, no CSS-in-JS
  libraries, no Bootstrap.
- Never hardcode API keys. All secrets read from environment variables via
  a .env file; .env must be in .gitignore; commit a .env.example instead.

## Testing & verification expectations
- After implementing the Gating Engine, write and run unit tests proving
  each rule in TRD.md §6's table (stock check, margin floor, discount
  ceiling, checkout confirmation) actually blocks or modifies a violating
  action.
- After implementing the frontend, use the browser agent to load the app,
  walk through: browse → add to cart → receive a recommendation → attempt
  an over-limit discount (confirm it's capped, not silently allowed) →
  checkout → view the audit panel and confirm the same session's decisions
  appear there.
- Do not mark a task complete without this end-to-end verification.

## What NOT to do
- Do not use live/production Razorpay keys anywhere.
- Do not let the frontend contain any policy/gating logic — all policy
  decisions happen server-side and must not be bypassable from the client.
- Do not silently swap the LLM provider, model, or database choice above.
- Do not skip Planning Mode for anything touching the gating engine, the
  data model, or the Razorpay integration — these are the parts a
  buildathon panel will scrutinize most closely.