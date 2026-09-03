# CartMind

**An AI upsell & cross-sell agent that grows merchant revenue — without ever giving an LLM unsupervised access to money.**

Built for the **Razorpay AI Buildathon 2026 — Track 01: AI Growth & Agentic Commerce**.

> Every money action this agent proposes is explainable, bounded, and gated by deterministic rules before it executes. Nothing the LLM says can directly move a discount, a cart total, or a payment — see [How the gate works](#how-the-gate-works) below.

---

## The problem

Merchants lose upsell revenue because it's either static ("customers also bought...") or fully manual. Conversational AI agents can close that gap — but only if they can be trusted not to misuse the influence they're given over pricing and checkout. CartMind is built around that trust problem, not just the recommendation problem.

## What it does

- A shopper chats naturally with an AI agent while browsing a demo storefront.
- The agent proactively recommends complementary/upgraded products at the right moment.
- The agent can propose a discount or move to checkout — but every proposal is validated against hard rules (stock, margin floor, discount ceiling, explicit user confirmation) before anything executes.
- A live **audit panel** shows every decision the system has ever made, approved or blocked, with a plain-English reason.
- Checkout completes via a real Razorpay **test-mode** payment.
- One failure scenario is deliberately engineered and demonstrated recovering gracefully (see TRD.md §9).

## How the gate works

```
User: "any chance of a discount on this?"
   → LLM proposes: apply_discount(percent=35, reason="...")
   → Gate checks: 35% > 20% ceiling → BLOCKED, capped to 20%
   → Audit log: { action: apply_discount, proposed: 35%, decision: MODIFIED,
                  rule_triggered: "max_discount_ceiling", applied: 20% }
   → Agent replies using the GATE's outcome, not its own proposal
```

The LLM never talks to Razorpay directly. It only ever proposes a structured action; a plain deterministic Python function decides what actually happens. Full design in `TRD.md` §6.

## Architecture

See `TRD.md` §1 for the full diagram. In short:

```
React Frontend → FastAPI Backend → [LLM proposes] → [Gate validates] → [Executor acts] → Razorpay (test mode)
                                                              ↓
                                                        Audit Log (SQLite)
```

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | React, Vite, Tailwind CSS |
| Backend | FastAPI (Python) |
| LLM | Groq API — `llama-3.3-70b-versatile`, function calling |
| Payments | Razorpay Python SDK (test mode) |
| Database | SQLite (SQLModel) |
| Automation (stretch) | n8n webhook for cart-abandonment follow-up |

## Getting started

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env   # add your GROQ_API_KEY and RAZORPAY test keys
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The frontend expects the backend at `http://localhost:8000` (configurable via `frontend/.env`).

### Environment variables

| Variable | Where | Description |
|---|---|---|
| `GROQ_API_KEY` | backend/.env | Groq API key for the LLM |
| `RAZORPAY_KEY_ID` | backend/.env | Razorpay test-mode key ID |
| `RAZORPAY_KEY_SECRET` | backend/.env | Razorpay test-mode key secret |
| `VITE_API_BASE_URL` | frontend/.env | Backend URL |

## Folder structure

```
cartmind/
├── backend/
│   ├── main.py
│   ├── agent/           # reasoning layer + tool schema
│   ├── gate/             # deterministic policy engine
│   ├── models/           # SQLModel data models
│   ├── razorpay_client.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/   # Storefront, Chat, Cart, AuditPanel
│   │   └── App.jsx
│   └── package.json
├── docs/
│   ├── architecture.png
│   └── metrics-report.md
├── PRD.md
├── TRD.md
└── README.md
```

## Measured impact

_Fill in after running the synthetic A/B script described in `TRD.md` §10:_

- AOV lift (agent-on vs agent-off): **TBD**
- Upsell acceptance rate: **TBD**
- Discount-rule block rate (proof the gate isn't a no-op): **TBD**

## What broke, and how it was fixed

_Razorpay's panel explicitly asks for this — fill in honestly as you build, don't reverse-engineer a clean story after the fact._

- Issue:
- Root cause:
- Fix:

## Demo

- 5-minute pitch video: `<link>`
- Live deployment (if available): `<link>`

## License

MIT — built as a submission for the Razorpay AI Buildathon 2026.
