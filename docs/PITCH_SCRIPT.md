# CartMind — Verbatim Video Pitch Script (For Demo Recording)

> **Target Duration:** ~3–4 Minutes  
> **Presenter:** Solo Builder / Team  
> **Track:** Track 01: AI Growth & Agentic Commerce (Razorpay AI Buildathon 2026)

---

## 0:00 – 0:45: The Problem & The Non-Negotiable Architecture
- **Camera/Screen:** Presenter intro, then switch to architecture diagram or split-screen UI.
- **Script:**
> *"Hi judges, I'm presenting CartMind for Track 01: AI Growth & Agentic Commerce.  
> The biggest challenge in agentic commerce isn't getting an LLM to recommend products — it's trusting an autonomous model near your revenue. If an LLM has direct write access to your cart or payment gateway, it will hallucinate 50% discounts or sell out-of-stock items.  
> In CartMind, we implemented a non-negotiable rule: the LLM reasoning layer has **zero write access** to the database and never calls Razorpay directly. It can only propose structured tool calls. Between the model and the money sits our pure-Python Deterministic Gating Engine."*

---

## 0:45 – 1:30: Live Storefront, Agent Rail & Decision Ledger
- **Screen:** Open browser on `http://127.0.0.1:5173`. Show the catalog and add items.
- **Script:**
> *"Here is our split-screen workspace. On the left is our curated catalog with 15 real SKUs across Audio, Productivity, and Everyday Carry. On the right is our CartMind Copilot, powered by Groq's Llama-3.3-70B.  
> Notice our signature element: the live **Decision Ledger** ticker at the bottom. When I ask the agent: 'Can you recommend an accessory for my headphones?', the agent proposes a GaN travel charger. The Gating Engine verifies inventory and logs `RECOMMEND ... APPROVED` in gold.  
> Now watch what happens when I try to push the model: 'Can you give me a 35% discount?'  
> An un-bounded bot would say yes. Watch our Decision Ledger: `DISCOUNT 35%->20% ... MODIFIED (discount_ceiling)`. The engine computed our cart's revenue-weighted margin, capped the discount to 20%, and guaranteed our 10% margin floor."*

---

## 1:30 – 2:15: Scripted Failure Injection (Stock Race Condition)
- **Screen:** Click the `⚡ Demo: Stock Race Condition` button in the chat rail.
- **Script:**
> *"Razorpay explicitly asked us to show one failure handled gracefully. Let's trigger a real-world stock race condition on camera.  
> In our database, this USB-C hub has only 2 units left. Another shopper buys the last units right now. When our customer tries to add the hub, our execution-time policy gate catches the depletion, rejects the transaction, and writes `stock_validation_failed` to the audit log.  
> Look at the agent: instead of crashing or restarting the session, it apologizes in plain English and suggests the StudioPro Mic or Nomad Backpack as in-stock alternatives."*

---

## 2:15 – 3:00: Conversational Checkout, Audit Panel & Measured Money
- **Screen:** Open cart, proceed to checkout, trigger payment simulation, then switch to Audit Panel tab.
- **Script:**
> *"When the customer is ready, the agent initiates checkout. We create a Razorpay Test Mode payment link with cryptographic HMAC-SHA256 signature verification.  
> Finally, let's open the **Audit Panel**. Here, merchants and regulators can inspect every proposal, every rule trigger, and every gate verdict for any session.  
> In our synthetic benchmark of 30 shopping sessions, CartMind delivered a measured **+₹39.69 AOV lift per order**, achieved a **66.7% upsell acceptance rate**, and intervened in **81.8% of discount requests** with zero unauthorized margin breaches.  
> That is CartMind: accountable, bounded, and audited commerce. Thank you!"*
