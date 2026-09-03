"""
LLM Reasoning Layer for CartMind.
Uses the Groq API with 'llama-3.3-70b-versatile' and function/tool calling.
Only PROPOSES actions; never executes them directly.
"""

import json
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from backend.config import settings
from backend.agent.prompts import CARTMIND_SYSTEM_PROMPT, TOOLS_SCHEMA

try:
    from groq import Groq
except ImportError:
    Groq = None


class ToolCallProposal(BaseModel):
    name: str
    arguments: Dict[str, Any]
    call_id: Optional[str] = None


class AgentTurnProposal(BaseModel):
    content: str
    tool_calls: List[ToolCallProposal] = []


class AgentReasoner:
    """
    Reasoning layer interacting with Groq LLM.
    Emits structured tool calls following the bounded action schema.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        if self.api_key and Groq:
            self.client = Groq(api_key=self.api_key)
        else:
            self.client = None

    def _build_context_summaries(
        self,
        cart_items: List[Dict[str, Any]],
        catalog_products: List[Dict[str, Any]]
    ) -> tuple[str, str]:
        """Formats cart contents and catalog (strictly excluding margin_pct)."""
        if not cart_items:
            cart_summary = "Your cart is currently empty."
        else:
            cart_lines = [
                f"- [Product ID {item['product_id']}] {item['name']} x{item['qty']} (Price: ₹{item['price']:.2f}, Line Total: ₹{item['line_total']:.2f})"
                for item in cart_items
            ]
            cart_summary = "\n".join(cart_lines)

        catalog_lines = [
            f"- ID {p['id']}: {p['name']} (₹{p['price']:.2f}, Stock: {p['stock_qty']}, Category: {p['category']}) - {p['description']}"
            for p in catalog_products
        ]
        catalog_summary = "\n".join(catalog_lines)
        return cart_summary, catalog_summary

    def propose_turn(
        self,
        user_message: str,
        cart_items: List[Dict[str, Any]],
        catalog_products: List[Dict[str, Any]],
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> AgentTurnProposal:
        """
        Sends the conversational context to Groq API and returns the proposed assistant turn.
        If no Groq key is present, falls back to a deterministic rule-based proposer.
        """
        cart_summary, catalog_summary = self._build_context_summaries(cart_items, catalog_products)
        system_prompt = CARTMIND_SYSTEM_PROMPT.format(
            cart_summary=cart_summary,
            catalog_summary=catalog_summary,
        )

        # If live Groq client is configured, call Groq API
        if self.client:
            try:
                messages = [{"role": "system", "content": system_prompt}]
                if chat_history:
                    messages.extend(chat_history[-6:])  # Recent history
                messages.append({"role": "user", "content": user_message})

                response = self.client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    tools=TOOLS_SCHEMA,
                    tool_choice="auto",
                    temperature=0.2,
                    max_tokens=512,
                )

                choice = response.choices[0].message
                content = choice.content or ""
                tool_calls: List[ToolCallProposal] = []

                if choice.tool_calls:
                    for tc in choice.tool_calls:
                        try:
                            args = json.loads(tc.function.arguments)
                        except Exception:
                            args = {}
                        tool_calls.append(
                            ToolCallProposal(
                                name=tc.function.name,
                                arguments=args,
                                call_id=tc.id,
                            )
                        )

                return AgentTurnProposal(content=content, tool_calls=tool_calls)
            except Exception as e:
                # Log error and fall back gracefully
                print(f"[AgentReasoner] Groq API call failed: {e}. Falling back to deterministic proposer.")

        # Offline / Mock Fallback Proposer
        return self._offline_propose(user_message, cart_items, catalog_products)

    def _offline_propose(
        self,
        user_message: str,
        cart_items: List[Dict[str, Any]],
        catalog_products: List[Dict[str, Any]]
    ) -> AgentTurnProposal:
        """Deterministic proposer for offline development, tests, and CI."""
        msg_lower = user_message.lower()
        tool_calls: List[ToolCallProposal] = []
        content = ""

        # Check for discount request (e.g., "35% discount", "give me a deal")
        if any(w in msg_lower for w in ["discount", "deal", "offer", "off", "cheaper", "coupon"]):
            # Extract number if present
            match = re.search(r"(\d+)%", user_message)
            percent = float(match.group(1)) if match else 15.0
            tool_calls.append(
                ToolCallProposal(
                    name="apply_discount",
                    arguments={"percent": percent, "reason": "Shopper requested pricing incentive."}
                )
            )
            content = f"I've proposed a {percent:.0f}% discount for your cart. Let's see what our store policy approves!"

        # Check for checkout request
        elif any(w in msg_lower for w in ["checkout", "buy", "pay", "order now", "complete"]):
            confirmed = not any(q in msg_lower for q in ["how", "can i", "what if", "where"])
            tool_calls.append(
                ToolCallProposal(
                    name="initiate_checkout",
                    arguments={"confirmed_by_user": confirmed}
                )
            )
            content = "I'm initiating checkout for you now." if confirmed else "I can help you check out whenever you're ready!"

        # Check for recommendation request or cart interaction
        elif any(w in msg_lower for w in ["recommend", "suggest", "complement", "pair", "what else", "add-on"]):
            # Find a product not already in cart
            cart_product_ids = {i["product_id"] for i in cart_items}
            candidate = next((p for p in catalog_products if p["id"] not in cart_product_ids and p["stock_qty"] > 0), None)
            if candidate:
                tool_calls.append(
                    ToolCallProposal(
                        name="recommend_product",
                        arguments={
                            "product_id": candidate["id"],
                            "reason": f"Complementary upgrade for items in your cart."
                        }
                    )
                )
                content = f"I recommend checking out the {candidate['name']}. It pairs nicely with your cart!"
            else:
                content = "You have a great selection in your cart! Let me know if you'd like to proceed to checkout."
        else:
            content = "Welcome to CartMind! I can suggest accessories for your cart, check for discounts, or help you check out quickly. How can I help you today?"

        return AgentTurnProposal(content=content, tool_calls=tool_calls)


reasoner = AgentReasoner()
