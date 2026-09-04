# CartMind — Accountable AI Commerce Agent with Conversational Checkout

> **Razorpay AI Buildathon 2026 | Track 01: AI Growth & Agentic Commerce**  
> *"Every money action explainable, bounded and gated. Show the audit trail and one failure handled gracefully."*

---

## 📑 Table of Contents
1. [Executive Summary](#executive-summary)
2. [📸 Product Walkthrough & Screenshots](#-product-walkthrough)
3. [System Architecture](#system-architecture)
4. [The 5 Deterministic Gating Rules](#the-5-deterministic-gating-rules)
5. [Failure Injection Demo: Stock Race Condition](#failure-injection-demo-stock-race-condition-trdmd-9-option-a)
6. [Measured Economic Impact: Synthetic A/B Testing](#measured-economic-impact-synthetic-ab-testing-report-trdmd-10)
7. [Quickstart & Local Setup](#quickstart--local-setup)
8. [Verbatim 3-Minute Video Pitch Script (For Judges)](#verbatim-3-minute-video-pitch-script-for-judges)
9. [License & Compliance](#license--compliance)

---

## Executive Summary

**CartMind** is an autonomous AI upsell and cross-sell agent with conversational checkout built for online merchants. It monitors the shopper's cart in real time, recommends contextual complementary gear, negotiates bounded discounts, and completes checkout conversationally.

**The Core FinTech Innovation:**
Most AI shopping bots fail because they have un-bounded write access to databases or hallucinate unauthorized discounts (e.g. promising 50% or 90% off). CartMind enforces an architectural **Separation of Concerns**:
1. **The LLM Reasoning Layer** (Groq `llama-3.3-70b-versatile`) **only proposes** structured actions (`recommend_product`, `apply_discount`, `initiate_checkout`). It has **zero database write access** and can never touch Razorpay directly.
2. **The Deterministic Gating Engine** (Pure Python, zero LLM calls) validates every proposed action against 5 hard merchant policies before anything executes.
3. **The Decision Ledger & Audit Trail** records every proposal and gate decision 1:1 with human-readable justifications and HMAC-SHA256 signature verification.

---

## 📸 Product Walkthrough

| Screenshot | Feature & Explanation |
|---|---|
| ![Storefront & Catalog](docs/screenshots/01-storefront-catalog.png) | **1. Curated Storefront & Split-Screen UI**<br>Interactive catalog with 15 seeded SKUs across Audio, Productivity, and Everyday Carry. Real-time cart synchronization and luxury dark mode design system. |
| ![Contextual Recommendation](docs/screenshots/02-contextual-recommendation.png) | **2. AI Copilot Recommendations**<br>Groq LLM (`llama-3.3-70b-versatile`) proposes contextual gear based on the shopper's cart items using structured tool calls. |
| ![Decision Ledger Modified](docs/screenshots/03-decision-ledger-modified-discount.png) | **3. Live Decision Ledger & Margin Math**<br>When an over-limit discount (e.g. 35% or 90% jailbreak) is requested, the Gating Engine intercepts and modifies the discount to cap at the 10% hard margin floor with full financial math transparency. |
| ![Decision Audit View](docs/screenshots/04-audit-panel-trail.png) | **4. Full Decision Audit Trail & Exports**<br>Dedicated audit console recording 1:1 gate decisions, HMAC-SHA256 signatures, chronological timeline, and one-click CSV / JSON export. |
| ![Stock Failure Recovery](docs/screenshots/05-stock-failure-recovery.png) | **5. Failure Injection: Stock Race Condition**<br>Simulates execution-time inventory depletion. The server gate blocks the transaction, writes `stock_validation_failed` to audit log, and the agent offers available in-stock alternatives without crashing. |

---

## System Architecture

```mermaid
flowchart TD
    subgraph Frontend ["Client Workspace (React + Vite + Tailwind)"]
        UI[Storefront ~60%]
        Chat[AI Copilot Rail ~40%]
        Ledger[Live Monospace Decision Ledger]
    end

    subgraph Backend ["FastAPI Application (Port 8000)"]
        ChatRoute["POST /session/{id}/message"]
        CartRoute["POST /session/{id}/cart/items"]
        CheckoutRoute["POST /session/{id}/checkout"]
        
        subgraph ReasoningLayer ["Layer 1: Reasoning Layer (LLM)"]
            Reasoner["Groq API (llama-3.3-70b-versatile)"]
            Tools["Tool Calls: recommend_product | apply_discount | initiate_checkout"]
        end

        subgraph GatingLayer ["Layer 2: Deterministic Gating Engine (Pure Python)"]
            Gate["GatingEngine (Zero LLM Calls)"]
            R1["Rule 1: Stock Check (> 0)"]
            R2["Rule 2: Turn Cap (Max 1)"]
            R3["Rule 3: 10% Margin Floor"]
            R4["Rule 4: 20% Discount Ceiling"]
            R5["Rule 5: Checkout Confirmation"]
        end

        subgraph ExecutionLayer ["Layer 3: Action Executor & Persistence"]
            Executor["Action Executor (Sole DB Writer)"]
            DB[(SQLite via SQLModel)]
            Audit[(Immutable Audit Log & Gate Decisions)]
        end

        subgraph Payments ["Razorpay Integration (Test Mode)"]
            RZP["Razorpay Python SDK (Test Mode)"]
            Link["Payment Links with Explicit Callbacks"]
            Verifier["HMAC-SHA256 Dual Signature Verifier"]
            Webhook["Authoritative Webhook Listener"]
        end
    end

    Chat -->|1. Customer Message| ChatRoute
    ChatRoute -->|2. Context & History| Reasoner
    Reasoner -->|3. Proposes Tool Call| Tools
    Tools -->|4. Intercepts Proposal| Gate
    Gate -->|5. Evaluates Policies| R1 & R2 & R3 & R4 & R5
    Gate -->|6. Approved / Modified / Blocked| Executor
    Executor -->|7. Persists State & Decisions| DB & Audit
    Executor -->|8. Creates Payment Link| RZP
    RZP -->|9. Returns Payment Link & Order| Verifier
    Audit -->|10. Real-time Feed| Ledger
```

---

## The 5 Deterministic Gating Rules

All rules execute in pure Python (`backend/gate/engine.py`) with zero external API calls:

| Rule | Policy Name | Logic & Formula | Gate Decision |
|---|---|---|---|
| **Rule 1** | **Stock Check** | Validates $stock\_qty > 0$ at proposal time and $existing\_qty + requested \le stock\_qty$ at execution time. | `blocked` if out of stock |
| **Rule 2** | **Recommendation Turn Cap** | Limits agent to $\le 1$ product recommendation per conversational turn. | `blocked` if $\ge 2$ in turn |
| **Rule 3 & 4** | **Unified Margin Floor & Ceiling** | Computes cart's revenue-weighted margin: $\mu = \frac{\sum (price \times qty \times margin)}{\text{subtotal}}$.<br>Caps discount: $\min(20\%, \mu - 10\%)$. | `modified` (capped) with binding rule tagged |
| **Rule 5** | **Checkout Confirmation** | Requires explicit user confirmation (`confirmed_by_user=True`) before generating payment links. | `blocked` if unconfirmed |

---

## Failure Injection Demo: Stock Race Condition (TRD.md §9 Option A)

### Scenario:
A customer asks for a low-stock item (e.g. *UltraSpeed USB-C 100W Hub*, seeded with 2 units). While browsing, another customer claims the last unit.

### Graceful Recovery Behavior:
1. **At Execution Time**: When the customer accepts or adds the item, the server-side gate catches $stock\_qty == 0$.
2. **Audit Logging**: The gate blocks the insertion and immediately logs a `stock_validation_failed` event to the `audit_log` table.
3. **Conversational Recovery**: The agent does not crash or restart the session. It catches the block, apologizes, and proactively suggests in-stock alternatives (*StudioPro Mic* or *Nomad Backpack*).
4. **Live Verification**: Click the **`⚡ Demo: Stock Race Condition`** button in the AI Copilot to see this graceful recovery live in your browser.

---

## Measured Economic Impact: Synthetic A/B Testing Report (TRD.md §10)

Simulation of 30 distinct shopping sessions comparing **Control (Baseline, No Agent)** vs **Treatment (CartMind Agent)** across 15 seeded SKUs:

| Metric | Baseline (Control) | CartMind Agent | Measured Lift |
|---|---|---|---|
| **Average Order Value (AOV)** | **₹6,924.80** | **₹6,964.49** | **+₹39.69 lift per order** |
| **Gross Revenue (30 Orders)** | ₹207,744.00 | ₹208,934.80 | **+₹1,190.80 net incremental lift** |
| **Upsell Acceptance Rate** | N/A | **66.67%** | 20 of 30 offered recommendations accepted |
| **Margin Gate Interventions** | 0 | **81.82%** | 18 of 22 discount requests capped to 20% floor |
| **10% Hard Margin Floor Compliance** | 100% | **100%** | **0 unauthorized margin breaches** |

*Generated via `scripts/simulate_ab_test.py`. Full report in `docs/metrics-report.md`.*

---

## Quickstart & Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Groq API Key (Optional — deterministic fallback operates offline)
- Razorpay Test Keys (Optional — instant cryptographic simulation operates offline)

### 1. Backend Setup
```powershell
# Navigate to project root
cd c:\CartMind

# Activate virtual environment
.\backend\.venv\Scripts\Activate.ps1

# Run tests (All 26 unit & integration tests)
pytest backend/tests/ -v

# Start FastAPI backend
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Backend runs at: [http://127.0.0.1:8000](http://127.0.0.1:8000) (Interactive Swagger Docs: `/docs`).

### 2. Frontend Setup
```powershell
cd c:\CartMind\frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev -- --host 127.0.0.1 --port 5173
```
Frontend runs at: [http://127.0.0.1:5173](http://127.0.0.1:5173).

### 3. Run Synthetic A/B Benchmark
```powershell
python scripts/simulate_ab_test.py
```

---

## Verbatim 3-Minute Video Pitch Script (For Judges)

### 0:00 – 0:45: The Problem & The Non-Negotiable Architecture
> *"Hi judges, I'm presenting CartMind for Track 01: AI Growth & Agentic Commerce.  
> The biggest challenge in agentic commerce isn't getting an LLM to recommend products — it's trusting an autonomous model near your revenue. If an LLM has direct write access to your cart or payment gateway, it will hallucinate 50% discounts or sell out-of-stock items.  
> In CartMind, we implemented a non-negotiable rule: the LLM reasoning layer has **zero write access** to the database and never calls Razorpay directly. It can only propose structured tool calls. Between the model and the money sits our pure-Python Deterministic Gating Engine."*

### 0:45 – 1:30: Live Storefront, Agent Rail & Decision Ledger
> *(Show browser on http://127.0.0.1:5173)*  
> *"Here is our split-screen workspace. On the left is our curated catalog with 15 real SKUs. On the right is our CartMind Copilot, powered by Groq's Llama-3.3-70B.  
> Notice our signature element: the live **Decision Ledger** ticker. When I ask the agent: 'Can you recommend an accessory for my headphones?', the agent proposes an GaN travel charger. The Gating Engine verifies inventory and logs `RECOMMEND ... APPROVED` in gold.  
> Now watch what happens when I try to push the model: 'Can you give me a 35% discount?'  
> An un-bounded bot would say yes. Watch our Decision Ledger: `DISCOUNT 35%->20% ... MODIFIED (discount_ceiling)`. The engine computed our cart's revenue-weighted margin, capped the discount to 20%, and guaranteed our 10% margin floor."*

### 1:30 – 2:15: Scripted Failure Injection (Stock Race Condition)
> *(Click '⚡ Demo: Stock Race Condition')*  
> *"Razorpay explicitly asked us to show one failure handled gracefully. Let's trigger a real-world stock race condition on camera.  
> In our database, this USB-C hub has only 2 units left. Another shopper buys the last units right now. When our customer tries to add the hub, our execution-time policy gate catches the depletion, rejects the transaction, and writes `stock_validation_failed` to the audit log.  
> Look at the agent: instead of crashing or restarting the session, it apologizes in plain English and suggests the StudioPro Mic or Nomad Backpack as in-stock alternatives."*

### 2:15 – 3:00: Conversational Checkout, Audit Panel & Measured Money
> *(Click Cart -> Proceed to Checkout -> Instant Test Payment Simulation)*  
> *"When the customer is ready, the agent initiates checkout. We create a Razorpay Test Mode payment link with cryptographic HMAC-SHA256 signature verification.  
> Finally, let's open the **Audit Panel**. Here, merchants and regulators can inspect every proposal, every rule trigger, and every gate verdict for any session.  
> In our synthetic benchmark of 30 shopping sessions, CartMind delivered a measured **+₹39.69 AOV lift per order**, achieved a **66.7% upsell acceptance rate**, and intervened in **81.8% of discount requests** with zero unauthorized margin breaches.  
> That is CartMind: accountable, bounded, and audited commerce. Thank you!"*

---

## License & Compliance
Built strictly for the Razorpay AI Buildathon 2026. All payments executed in Razorpay Test Mode with synthetic credentials. Zero live cards charged.
