# Technical Requirements Document (TRD)
## CartMind — AI Upsell & Cross-Sell Agent with Conversational Checkout

---

## 1. System Architecture

```
                         ┌──────────────────────────┐
                         │        React Frontend      │
                         │  Storefront + Chat + Audit  │
                         │        Panel (Vite)         │
                         └─────────────┬────────────┘
                                       │ REST / SSE
                         ┌─────────────▼────────────┐
                         │       FastAPI Backend      │
                         │  ┌──────────────────────┐ │
                         │  │   Session & Cart API   │ │
                         │  └──────────────────────┘ │
                         │  ┌──────────────────────┐ │
                         │  │   Reasoning Layer (LLM) │ │──▶ Groq API
                         │  │  proposes tool calls    │ │   (llama-3.3-70b)
                         │  └──────────┬───────────┘ │
                         │             │ proposed action
                         │  ┌──────────▼───────────┐ │
                         │  │  Policy / Gating Engine │ │  (pure Python,
                         │  │  deterministic rules    │ │   zero LLM calls)
                         │  └──────────┬───────────┘ │
                         │      approved│  blocked    │
                         │  ┌──────────▼──┐  ┌──────▼────────┐
                         │  │ Action Executor│  │  Audit Logger  │
                         │  │ (Razorpay calls│  │ (every decision)│
                         │  │  cart updates) │  │                │
                         │  └──────┬───────┘  └────────────────┘
                         └─────────┼──────────────────┘
                                   │
                         ┌─────────▼─────────┐
                         │  Razorpay Test-Mode │
                         │  Orders / Payment   │
                         │  Links API          │
                         └────────────────────┘
                                   │
                         ┌─────────▼─────────┐
                         │   SQLite / Postgres │
                         │  products, sessions,│
                         │  recommendations,   │
                         │  gate_decisions,    │
                         │  orders, audit_log  │
                         └────────────────────┘
```

**The one architectural decision that matters most:** the Reasoning Layer never calls Razorpay, never writes to the cart, and never applies a discount directly. It only *proposes* a structured action. The Gating Engine is the only code path with write access to money-affecting state. This single decision is what turns "a chatbot with a nice prompt" into something that clears Razorpay's stated bar.

## 2. Component Responsibilities

| Component | Responsibility | Must NOT do |
|---|---|---|
| Reasoning Layer (LLM) | Interpret user intent, converse naturally, emit a structured tool call when action is warranted | Directly mutate cart/order state; call Razorpay; bypass the gate under any prompt |
| Policy/Gating Engine | Validate every proposed action against deterministic rules; approve, modify, or block; write the decision to the audit log | Use an LLM call to make the approve/block decision |
| Action Executor | Execute only gate-approved actions (update cart, call Razorpay) | Execute anything the gate didn't explicitly approve |
| Audit Logger | Persist every proposed action + gate decision + reason + timestamp | Silently drop blocked actions (blocked actions are audit-worthy too) |
| Frontend | Render storefront, chat, and a live audit/decision view | Contain any policy logic (all policy lives server-side, non-bypassable) |

## 3. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | React + Vite + Tailwind CSS | Fast iteration, matches the frontend-prompt design system, easy for Antigravity's browser agent to verify visually |
| Backend | FastAPI (Python) | You already have this pattern from Yash AI; async support suits streaming chat responses |
| LLM | Groq API, `llama-3.3-70b-versatile`, function/tool calling | Fast inference (sub-second), free/cheap tier, tool-calling support, reuses your existing integration pattern |
| Payments | `razorpay` Python SDK, test mode | Required by the track brief |
| Database | SQLite via SQLModel for the demo; note Postgres as the production path | Zero-ops for a buildathon timeline; schema is portable if you outgrow it |
| Automation (stretch) | n8n webhook for cart-abandonment follow-up | You already know this tool; cheap differentiator if time allows |
| Deployment | Frontend → Vercel/Netlify; Backend → Render/Railway free tier | Panel may want a live link, not just localhost |

## 4. Data Model

```
products
  id, name, price, stock_qty, margin_pct, category, description

cart_sessions
  id, created_at, status (active/checked_out/abandoned)

cart_items
  id, session_id (FK), product_id (FK), qty, added_at

agent_recommendations
  id, session_id (FK), proposed_action (json), reasoning_text,
  created_at

gate_decisions
  id, recommendation_id (FK), decision (approved/blocked/modified),
  reason_text, rule_triggered, decided_at

orders
  id, session_id (FK), razorpay_order_id, amount, status,
  created_at

audit_log
  id, session_id (FK), event_type, payload (json), created_at
```

`gate_decisions.rule_triggered` is worth calling out specifically in your pitch — it's what lets you say "here is the exact rule that fired" rather than "the system generally behaves safely."

## 5. API Contract (core endpoints)

| Method | Path | Purpose |
|---|---|---|
| GET | `/products` | List catalog |
| POST | `/session` | Start a cart session |
| POST | `/session/{id}/message` | Send a chat message; returns agent reply + any gate-approved UI updates |
| GET | `/session/{id}/cart` | Current cart state |
| POST | `/session/{id}/checkout` | Trigger gate-validated checkout → Razorpay order/payment link |
| GET | `/audit/{session_id}` | Full audit trail for a session (for the admin panel) |
| POST | `/admin/inject-failure` | Demo-only endpoint to trigger the engineered failure scenario on command |

## 6. Agent Design — The Bounded Action Schema

This is the single most important artifact for the buildathon panel. Define tool calls with a strict JSON schema; anything that doesn't validate is rejected by default (fail closed):

```json
{
  "tools": [
    {
      "name": "recommend_product",
      "description": "Propose ONE complementary or upgraded product to the shopper.",
      "parameters": {
        "product_id": "string, must exist in catalog",
        "reason": "string, max 140 chars, must reference cart contents"
      }
    },
    {
      "name": "apply_discount",
      "description": "Propose a percentage discount on the current cart.",
      "parameters": {
        "percent": "number, 0-100",
        "reason": "string, max 140 chars"
      }
    },
    {
      "name": "initiate_checkout",
      "description": "Propose moving the session to checkout.",
      "parameters": {
        "confirmed_by_user": "boolean, must be true"
      }
    }
  ]
}
```

**Gating Engine rules (deterministic, pure Python — no LLM involvement):**

| Rule | Enforced on | Effect if violated |
|---|---|---|
| Recommended product must be in stock | `recommend_product` | Blocked; agent told to pick another item |
| Max 1 recommendation per conversational turn | `recommend_product` | Second proposal in same turn blocked |
| Discount must not drop item below margin floor (e.g., 10%) | `apply_discount` | Blocked or capped to the max allowed discount |
| Discount ceiling (e.g., 20% absolute max) | `apply_discount` | Capped, not just blocked — shows "modified" as a third decision type |
| Checkout requires explicit user confirmation flag | `initiate_checkout` | Blocked if the LLM tries to checkout without the user having said yes |

Every row in this table becomes a line in your pitch script: *"here's a rule, here's the code that enforces it, here's the audit log entry it produced."*

## 7. Razorpay Integration Plan

1. Create a test-mode Razorpay account; generate test API keys.
2. Use the Orders API to create an order once checkout is gate-approved.
3. Use a Payment Link (or Razorpay Checkout.js in test mode) so the demo can show an actual test payment being completed on camera.
4. Handle Razorpay's documented test failure card/UPI ID to trigger a realistic payment failure for your graceful-failure demo (see §9).
5. Never store live keys in the repo — `.env` + `.gitignore`, documented in README.

## 8. Audit Trail Design

- Every `agent_recommendations` row is paired 1:1 with a `gate_decisions` row — nothing is proposed without a recorded outcome.
- Admin panel view: a chronological feed per session — timestamp, proposed action, decision (color-coded approved/blocked/modified), and the reason string, in plain English.
- This view is *the* artifact to have open during the pitch video — narrating a live decision from it is worth more than any slide.

## 9. Failure Injection Plan (pick one, build it deliberately)

**Option A — Stock race condition:** Item goes out of stock in the few seconds between the agent recommending it and the user accepting it.
- Expected behavior: the gate re-validates stock at execution time (not just at proposal time), blocks the stale action, and the agent apologizes and offers the next-best in-stock alternative — without restarting the conversation.

**Option B — Razorpay payment failure:** Use Razorpay's documented test-mode failure card.
- Expected behavior: the backend catches the failed payment webhook/response, the agent explains what happened in plain language, and offers to retry or pick a different payment method — without leaving the cart in an inconsistent state.

Pick **one**, build it properly, and script it into your pitch video verbatim — "here I'm about to trigger X, watch what the agent does." A rehearsed failure demo reads far better on a panel than an unplanned crash.

## 10. Metrics Computation (synthetic A/B)

1. Script 30–50 synthetic cart sessions (can be scripted, not live users) covering a spread of cart sizes/categories.
2. Run each session twice: once with the agent active, once with recommendations disabled.
3. Compute: average order value (AOV) delta, upsell acceptance rate, discount-rule block rate (proof the gate is actually doing something, not a no-op).
4. Report these three numbers in the README and the pitch — this is your answer to "show measured money" that every track's bar keeps repeating.

## 11. Security Notes

- API keys (Groq, Razorpay) in `.env`, never committed; `.env.example` committed instead.
- Basic prompt-injection defense: the system prompt instructs the model that tool-call parameters are the *only* channel of effect — user text can never directly set a discount percent or bypass a rule, because the gate re-validates every tool call regardless of what the conversation says. Worth a one-line mention in your pitch given your Sentinel AI background — it's a natural, honest callback to prior work.
- Rate-limit the chat endpoint to prevent runaway LLM cost during the demo period.

## 12. Deployment Plan

- Backend: Render or Railway free tier, FastAPI + SQLite (or their managed Postgres).
- Frontend: Vercel or Netlify, pointed at the deployed backend URL via env var.
- Keep a `docs/architecture.png` (export of the diagram in §1) in the repo — Razorpay explicitly asks for architecture documentation alongside the code.

## 13. Suggested Day-by-Day Build Plan (10–12 days)

| Days | Focus |
|---|---|
| 1–2 | Razorpay test-mode integration in isolation (de-risk the unfamiliar part first) |
| 3–4 | Data model + FastAPI backend skeleton + catalog/cart endpoints |
| 5–6 | LLM reasoning layer + tool-calling schema + Gating Engine + audit logging |
| 7–8 | Frontend: storefront, chat widget, cart, checkout flow (use FRONTEND_PROMPT.md) |
| 9 | Admin/audit panel UI |
| 10 | Failure injection scenario, scripted and tested end-to-end |
| 11 | Synthetic A/B script + metrics report |
| 12 | Polish, record pitch video, write "what broke" section of README |
