# Product Requirements Document (PRD)
## CartMind — AI Upsell & Cross-Sell Agent with Conversational Checkout
**Track 01 — AI Growth & Agentic Commerce | Razorpay AI Buildathon 2026**

---

## 1. One-Liner

CartMind is an AI shopping agent that watches a merchant's cart in real time, recommends the right upsell or cross-sell at the right moment, and can complete the purchase conversationally — while every money-adjacent action it takes is deterministically validated, logged, and explainable before it ever touches Razorpay.

## 2. Problem Statement

Razorpay's own brief for this track frames the "why now" as agent-to-agent and agent-to-merchant commerce becoming the open problem of the year (NPCI's UAP, ACP/AP2/x402 protocol race, Razorpay's own in-app pilots). The underlying merchant problem is simpler: most merchants leave revenue on the table because upsell/cross-sell logic today is either static ("customers who bought X also bought Y" pop-ups) or fully manual. A conversational agent can close that gap — but only if merchants (and regulators, and Razorpay's own panel) can trust that an autonomous agent isn't given a blank check over pricing, discounts, or checkout.

**The real problem CartMind solves is not "can an LLM recommend products" — it's "can an LLM be given real influence over a merchant's revenue without being given the power to misuse it."**

## 3. Goals

- G1: Increase a simulated merchant's average order value (AOV) via contextual, conversational upsell/cross-sell — and *measure* the lift, not just claim it.
- G2: Every action the agent proposes (recommend item X, apply discount Y, initiate checkout) passes through a deterministic policy gate before execution — no LLM output touches Razorpay's API directly.
- G3: A full audit trail exists for every recommendation and every gate decision (approved or blocked, with a stated reason).
- G4: The system degrades gracefully under at least one real failure mode (see §9) instead of breaking the conversation.
- G5: A Razorpay test-mode transaction can be completed end-to-end, initiated from the conversational flow.

## 4. Non-Goals (v1)

- Real merchant onboarding or multi-tenant merchant accounts.
- Real payment processing (test mode only — this is explicit in Razorpay's own brief).
- Personalization based on real user history/CRM data (a synthetic session-based cart is sufficient).
- Training or fine-tuning a custom model — a hosted LLM with function-calling is sufficient and expected.
- Mobile app — a responsive web demo is sufficient.

## 5. Target Users

| User | What they need from CartMind |
|---|---|
| **Shopper** (demo persona) | A natural way to ask questions, get relevant suggestions, and check out without hunting through menus |
| **Merchant** (demo persona) | Confidence that the agent can't discount below margin, recommend out-of-stock items, or run away with checkout logic |
| **Razorpay panel** (the actual audience that matters for this deliverable) | Proof that you understand *why* explainability and bounding matter in a fintech context, not just that you can call an LLM API |

## 6. Core User Stories

1. As a shopper, I add a product to my cart and the agent proactively suggests one relevant complementary item, with a one-line reason.
2. As a shopper, I can ask the agent "any better deal?" and it either offers a policy-compliant discount or explains why it can't.
3. As a shopper, I can complete checkout conversationally ("yes, check me out") and the agent hands off to a real Razorpay test-mode payment link.
4. As a merchant/judge, I can open an audit panel and see, for any session, every recommendation the agent made, whether it was approved or blocked, and why.
5. As a merchant/judge, I can trigger a failure scenario (item goes out of stock mid-conversation, or a test payment fails) and watch the agent recover without breaking the session.

## 7. Functional Requirements

**Must-have (v1 / demo-critical):**
- FR1: Product catalog with at least 12–15 SKUs across 2–3 categories, including price, stock, and margin metadata.
- FR2: Conversational chat interface embedded in the storefront.
- FR3: LLM agent that can call a bounded set of tools: `recommend_product`, `apply_discount`, `initiate_checkout` (see TRD §6 for the exact schema).
- FR4: Deterministic policy engine that validates every tool call against rules (stock, margin floor, max discount %, one-recommendation-per-turn cap) before it executes.
- FR5: Persistent audit log recording every proposed action, the gate's decision, and the reason.
- FR6: Admin/audit view showing the log in human-readable form, filterable by session.
- FR7: Razorpay test-mode integration — Orders API or Payment Links — triggered only after gate approval.
- FR8: One deliberately engineered failure path with a defined graceful-recovery behavior.
- FR9: A synthetic A/B report comparing agent-on vs agent-off sessions on AOV and upsell acceptance rate.

**Should-have (if time allows):**
- FR10: Agent-readable catalog (structured JSON-LD style product feed) — a secondary Track 01 example direction, useful as a stretch feature that broadens your pitch.
- FR11: Campaign orchestrator hook — an n8n workflow that triggers a follow-up email/notification after cart abandonment (you already have n8n experience — cheap to add, high judge-visibility).

**Won't-have (v1):**
- Multi-agent negotiation between an AI buyer and CartMind (interesting but out of scope for a solo 10–14 day build).

## 8. Non-Functional Requirements

| Requirement | Target |
|---|---|
| Explainability | Every agent action has a one-sentence, human-readable justification stored alongside it |
| Boundedness | Zero code paths where an LLM response is passed directly to a Razorpay API call without gate validation |
| Auditability | 100% of proposed actions logged, including blocked ones |
| Latency | Agent response under ~3s for a typical turn (Groq's inference speed makes this comfortable) |
| Graceful degradation | The defined failure scenario never produces a raw stack trace or dead-end chat in the demo |
| Security | No API keys committed to the repo; `.env` gitignored; basic prompt-injection resistance (system prompt cannot be overridden to bypass the gate) |

## 9. Success Metrics (mapped directly to Razorpay's stated bar)

Razorpay's own bar for this track: *"Every money action explainable, bounded and gated. Show the audit trail and one failure handled gracefully."* Your PRD success criteria should be gradeable against exactly that:

1. Can you point to a specific line of code where a proposed discount/checkout is rejected if it violates a rule? (bounded)
2. Can you open the audit panel live and narrate a real decision from it? (explainable + audit trail)
3. Can you break the demo on purpose and show it recovering, on camera, in the pitch video? (graceful failure)
4. Can you show one number — AOV lift or upsell acceptance rate — computed from your own synthetic test, not asserted? (measured impact)

## 10. Risks & Assumptions

| Risk | Mitigation |
|---|---|
| Razorpay test-mode API quirks eat build time | Integrate Razorpay first, in isolation, before wiring the agent — de-risk the unfamiliar part early |
| LLM hallucinates a tool call outside the allowed schema | Function-calling with a strict JSON schema + gate rejects anything malformed by default (fail closed, not open) |
| Demo feels like "just a chatbot" to the panel | Lead the pitch with the gating/audit story, not the chat UI — that's the actual differentiator per the brief |
| Scope creep into a full e-commerce platform | Timebox the storefront UI; the judged surface area is the agent + gate + audit trail, not the shop's polish |

## 11. Deliverables Checklist (per Razorpay's submission requirements)

- [ ] Public GitHub repository
- [ ] Architecture documentation (this kit's TRD.md + README.md)
- [ ] 5-minute pitch video covering: problem, approach, live demo, one thing that broke and how you fixed it
- [ ] Measured result (AOV/acceptance-rate delta) shown on camera, not just claimed
