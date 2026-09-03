# Frontend Prompt — CartMind UI

## A note on motionsites.ai

I checked motionsites.ai directly. Its Fintech/SaaS category (entries like "Finlytic AI Agent," "Nickel Payments," "Synapse Dark Hero") is the right *neighborhood* for CartMind — dark, glass-panelled, data-forward AI/fintech dashboards. But every prompt on that site is a paid, commercial product, so I'm not copying or paraphrasing any of their actual prompt text here — that would be reproducing someone else's IP inside your buildathon submission, which is the opposite of what you want a judge to find.

What follows instead is an **original design system**, built the same way a studio would build one for this exact brief — not a generic dark-SaaS template. If you want, you can still browse motionsites.ai's Fintech/SaaS section yourself for extra visual reference or purchase a prompt you like — but paste it into a *separate* experiment, not into CartMind's submission repo.

---

## Design Brief

**Subject:** An AI commerce agent whose entire value proposition is that it's accountable — every recommendation and every money action is visible, explainable, and reversible-by-rule.

**The design problem this needs to solve:** most AI-agent UIs hide their reasoning behind a chat bubble. CartMind's whole pitch is the opposite — the reasoning and the guardrails need to be *as visible as the shopping itself*, not tucked behind a settings page. The UI has to make "bounded and audited" feel like a visible, almost physical property of the product, not a backend implementation detail.

## Design Token System

**Color — "Ink & Signal."** Rejected the two most common AI-generated defaults (warm cream + terracotta; near-black + a single acid-green/vermilion accent) in favor of a palette where each accent has exactly one semantic job — because this product's whole point is that colors (decisions) mean something specific, not decorative:

| Token | Hex | Role |
|---|---|---|
| `ink` | `#0B0E14` | Base background — deep navy-black, not pure black |
| `panel` | `#141A26` | Card/panel surfaces |
| `paper` | `#F3F1EA` | Primary text — warm off-white, not stark white |
| `slate` | `#566073` | Secondary text, borders, dividers |
| `signal-gold` | `#E8B84F` | Reserved exclusively for "approved" decisions and value/price emphasis |
| `agent-cyan` | `#4FD1C5` | Reserved exclusively for the agent's own voice/thinking state — never used elsewhere |
| `alert-coral` | `#E8614F` | Reserved exclusively for "blocked" decisions — never used decoratively |

**Typography — two-role pairing, one continuity nod:**
- Display: **Cabinet Grotesk** (via Fontshare, free) — a confident geometric grotesk for headings and the CartMind wordmark. Used with restraint: headings only.
- Body: **Inter** — for chat text, product copy, UI labels.
- Utility/mono: **IBM Plex Mono** — for every number, timestamp, and the Decision Ledger. (This deliberately echoes the mono face already used in your Yash AI project — a small signature across your own portfolio of work, and mono genuinely earns its place here: it's what makes the ledger read like an audit log rather than decoration.)

**Layout — Split-Screen Commerce Workspace:**
The page is never a single-column chatbot. It's always shopping-experience-left, accountability-rail-right — because a judge should be able to watch a shopper interact AND see the guardrail fire in the same glance, without switching views.

```
┌─────────────────────────────────────────────────┬───────────────────────┐
│  Storefront / Product / Cart / Checkout           │   Agent Rail           │
│  (≈62% width)                                     │   (≈38% width)         │
│                                                    │   ┌─────────────────┐ │
│  [product grid]                                   │   │  Chat            │ │
│  [product detail]                                 │   └─────────────────┘ │
│  [cart drawer]                                    │   ┌─────────────────┐ │
│  [checkout]                                       │   │  Decision Ledger  │ │
│                                                    │   │  (live ticker)    │ │
│                                                    │   └─────────────────┘ │
└─────────────────────────────────────────────────┴───────────────────────┘
```

On mobile: the Agent Rail collapses into a bottom sheet/tab, but the Decision Ledger stays reachable within one tap — never buried three menus deep. Accountability should feel just as available on mobile as the shopping itself.

**Signature element — The Decision Ledger.**
This is the one thing this UI should be remembered by. A live, timestamped, monospace feed of every gate decision as it happens — styled like a trading terminal log, not a chat log:

```
09:41:02   RECOMMEND        ProShield Case         ✓ APPROVED
09:41:14   DISCOUNT 35%→20% margin floor rule       ◐ MODIFIED
09:41:20   CHECKOUT         confirmed by user       ✓ APPROVED
09:41:31   RECOMMEND        USB-C Hub (out of stock) ✕ BLOCKED
```

- Gold row = approved. Coral row = blocked. Slate/muted row = modified.
- New entries slide in from the top with a brief highlight flash — the only animation this component gets. No particle effects, no glow-everything — restraint is what makes it read as a real audit tool rather than a marketing page.
- The **same component**, at full width and filterable by session, becomes the Admin/Audit screen. It's not a separate design — it's the shopper-facing rail's own log, zoomed in. That repetition is deliberate: it shows the judge that nothing shown to the merchant is different from what happened live.

## Screen-by-Screen Spec

1. **Storefront** — product grid (3 columns desktop / 1 mobile), each card: image, name, price in `signal-gold`, a small stock pill (in-stock = slate outline, low-stock = coral outline).
2. **Product detail** — larger image, description, add-to-cart button; triggers the agent's first recommendation in the rail if relevant.
3. **Cart drawer** — slides in from the right, overlapping the Agent Rail slightly to visually tie cart changes to agent activity.
4. **Chat (top of Agent Rail)** — agent messages use `agent-cyan` accents (avatar ring, "thinking" indicator) — this color must never appear anywhere else in the UI, so its meaning stays singular.
5. **Decision Ledger (bottom of Agent Rail)** — as specified above; always visible, never a modal you have to open.
6. **Checkout** — a focused, distraction-free step; on success, show the Razorpay test-mode confirmation and log the final ledger entry live.
7. **Admin/Audit view** (`/audit`) — full-width Decision Ledger, session filter dropdown, export button. This is the screen to have open during the pitch video.

## Copy-Paste Master Prompt (paste into Antigravity for the frontend build)

```
Build the CartMind frontend: React + Vite + Tailwind CSS, functional
components and hooks only, no class components, no Bootstrap or CSS-in-JS.

DESIGN SYSTEM — follow exactly, do not substitute a generic template:

Colors (Tailwind config, extend theme):
  ink: #0B0E14        (base background)
  panel: #141A26      (card/panel surfaces)
  paper: #F3F1EA       (primary text)
  slate: #566073       (secondary text/borders)
  signal-gold: #E8B84F (APPROVED decisions + price emphasis — nowhere else)
  agent-cyan: #4FD1C5  (agent voice/avatar only — nowhere else)
  alert-coral: #E8614F (BLOCKED decisions only — nowhere else)

Typography:
  Display font "Cabinet Grotesk" (load from Fontshare) for headings/wordmark
  only, used sparingly.
  Body font "Inter" for all UI text and chat copy.
  Mono font "IBM Plex Mono" for every number, timestamp, and the entire
  Decision Ledger component.

Layout: a persistent split-screen workspace. Left ~62% is the storefront
(product grid → product detail → cart drawer → checkout). Right ~38% is a
fixed "Agent Rail" containing, top to bottom: (1) a chat panel where agent
messages use the agent-cyan accent, (2) the Decision Ledger — a live,
auto-scrolling, monospace, timestamped feed of gate decisions, color-coded
gold/approved, coral/blocked, slate/modified, with new entries sliding in
from the top with a brief highlight flash and no other animation. On
mobile, collapse the Agent Rail into a bottom sheet reachable in one tap;
never hide the Decision Ledger more than one interaction deep.

Build these screens: Storefront (3-col grid desktop, 1-col mobile, product
cards with image/name/price-in-gold/stock pill), Product Detail, Cart
Drawer (slides from the right), Checkout (focused single-purpose screen,
shows Razorpay test-mode confirmation on success), and a separate /audit
route that renders the Decision Ledger at full width with a session
filter dropdown and an export button — reuse the same Ledger component,
don't rebuild it.

Accessibility and restraint: visible keyboard focus states throughout,
respect prefers-reduced-motion (disable the ledger slide-in and any other
motion when set), and keep the only "wow" moment as the Ledger's live
updates — no particle backgrounds, no gratuitous 3D, no glow on every
element. This product's whole pitch is trustworthy restraint, and the UI
should feel that way before a single line of copy explains it.

Wire the frontend to the backend endpoints defined in TRD.md §5. Do not
implement any policy/gating logic in the frontend — it only renders what
the backend's gate has already decided.

After building, use the browser agent to walk through: browse products →
trigger a recommendation → attempt checkout → view the /audit page for
that session, and take screenshots at each step for my review.
```
