import React, { useState, useRef, useEffect } from 'react';
import { useCart } from '../context/CartContext';
import { Send, Sparkles, Plus, Check, Loader2, Bot, ArrowRight, ShieldCheck } from 'lucide-react';

export default function ChatPanel() {
  const { chatMessages, sendMessage, isThinking, addToCart } = useCart();
  const [inputText, setInputText] = useState('');
  const [addingId, setAddingId] = useState(null);
  const messagesEndRef = useRef(null);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isThinking]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputText.trim() || isThinking) return;
    sendMessage(inputText);
    setInputText('');
  };

  const handleQuickPrompt = (prompt) => {
    if (isThinking) return;
    sendMessage(prompt);
  };

  const handleAcceptRecommendation = async (productId) => {
    setAddingId(productId);
    await addToCart(productId, 1);
    setAddingId(null);
  };

  const handleTriggerStockFailureDemo = async () => {
    if (isThinking) return;
    setIsThinking(true);
    try {
      // 1. Deplete SKU 15 stock in background (simulating another buyer claiming it)
      await fetch('http://127.0.0.1:8000/products/15/deplete-stock', { method: 'POST' });

      // 2. Add user chat prompt asking for the low-stock item
      const userMsg = {
        id: `usr_${Date.now()}`,
        role: 'user',
        text: 'Can I add the UltraSpeed USB-C 100W Hub to my cart?',
        timestamp: new Date().toISOString(),
      };
      setChatMessages((prev) => [...prev, userMsg]);

      // 3. Attempt to add the depleted item -> caught by execution-time gate!
      const sid = sessionId || (await initSession());
      const addRes = await fetch(`http://127.0.0.1:8000/session/${sid}/cart/items`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: 15, qty: 1 }),
      });

      if (!addRes.ok) {
        await refreshAudit(sid);
        setTimeout(() => {
          const recoveryMsg = {
            id: `agt_${Date.now()}`,
            role: 'assistant',
            text: "⚠️ STOCK RACE CONDITION CAUGHT BY SERVER GATE:\nI apologize! Another customer claimed the last UltraSpeed USB-C 100W Hub while you were shopping. Our deterministic policy gate blocked this transaction at execution time to protect order integrity.\n\nWould you like me to recommend the StudioPro Mic or Nomad Backpack as an available alternative?",
            timestamp: new Date().toISOString(),
          };
          setChatMessages((prev) => [...prev, recoveryMsg]);
          setIsThinking(false);
        }, 600);
      } else {
        setIsThinking(false);
      }
    } catch (err) {
      console.error('Failure injection demo error:', err);
      setIsThinking(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-panel border border-panel-border rounded-2xl overflow-hidden shadow-2xl">
      {/* Agent Header */}
      <div className="px-5 py-3.5 border-b border-panel-border bg-ink/90 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          {/* Glowing agent-cyan avatar ring */}
          <div className="relative flex items-center justify-center w-9 h-9 rounded-full bg-ink border-2 border-agent-cyan shadow-[0_0_16px_rgba(79,209,197,0.35)]">
            <Bot className="w-5 h-5 text-agent-cyan" />
            <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-400 border-2 border-ink"></span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-display font-bold text-base text-paper tracking-tight">CartMind Copilot</span>
              <span className="px-2 py-0.5 rounded-full text-[9px] font-mono uppercase bg-agent-cyan/15 text-agent-cyan border border-agent-cyan/30 font-bold">
                GROQ LLAMA-3.3-70B
              </span>
            </div>
            <p className="text-[10px] font-mono text-slate">Conversational Upsell & Checkout Agent</p>
          </div>
        </div>

        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-ink border border-panel-border text-[10px] font-mono text-slate">
          <ShieldCheck className="w-3.5 h-3.5 text-signal-gold" />
          <span>Gated</span>
        </div>
      </div>

      {/* Message Stream */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4 font-sans text-sm selection:bg-agent-cyan/20">
        {chatMessages.map((msg) => {
          const isUser = msg.role === 'user';

          return (
            <div
              key={msg.id}
              className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} space-y-2`}
            >
              <div
                className={`max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-md ${
                  isUser
                    ? 'bg-signal-gold text-ink font-semibold rounded-tr-none'
                    : 'bg-ink border border-panel-border text-paper rounded-tl-none font-normal'
                }`}
              >
                {msg.text}
              </div>

              {/* Actionable Decision Cards (TRD.md §6 & Phase 5 spec) */}
              {!isUser && msg.decisions && msg.decisions.length > 0 && (
                <div className="w-full max-w-[94%] space-y-2.5 pt-1">
                  {msg.decisions.map((dec, idx) => {
                    // Recommendation Card
                    if (dec.tool_name === 'recommend_product' && dec.action_data) {
                      const item = dec.action_data;
                      const isApproved = dec.decision === 'approved';

                      return (
                        <div
                          key={idx}
                          className="bg-ink border border-panel-border rounded-xl p-3.5 flex items-center gap-4 shadow-xl animate-fadeIn"
                        >
                          <img
                            src={item.image_url || 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=200&q=80'}
                            alt={item.name}
                            className="w-16 h-16 object-cover rounded-lg bg-panel shrink-0 border border-panel-border"
                          />
                          <div className="flex-1 min-w-0">
                            <span className="text-[9px] font-mono font-bold tracking-wider uppercase px-2 py-0.5 rounded-full bg-signal-gold/15 text-signal-gold border border-signal-gold/30">
                              RECOMMENDED COMPLEMENT
                            </span>
                            <h4 className="font-display font-bold text-sm text-paper truncate mt-1">
                              {item.name}
                            </h4>
                            <p className="font-mono text-sm font-black text-signal-gold mt-0.5">
                              ₹{item.price?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                            </p>
                          </div>
                          {isApproved ? (
                            <button
                              onClick={() => handleAcceptRecommendation(item.product_id)}
                              disabled={addingId === item.product_id}
                              className="px-4 py-2 rounded-xl bg-signal-gold text-ink font-bold text-xs uppercase tracking-wider flex items-center gap-1 hover:opacity-90 active:scale-95 transition-all shrink-0 shadow-md shadow-signal-gold/10"
                            >
                              {addingId === item.product_id ? (
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              ) : (
                                <>
                                  <Plus className="w-3.5 h-3.5 stroke-[3]" />
                                  Add
                                </>
                              )}
                            </button>
                          ) : (
                            <span className="text-[11px] font-mono text-alert-coral font-bold uppercase">
                              Blocked
                            </span>
                          )}
                        </div>
                      );
                    }

                    // Discount Verdict Pill
                    if (dec.tool_name === 'apply_discount' && dec.action_data) {
                      return (
                        <div
                          key={idx}
                          className={`rounded-xl px-4 py-3 text-xs font-mono border flex items-center justify-between shadow-md animate-fadeIn ${
                            dec.decision === 'modified'
                              ? 'bg-slate/15 border-slate/40 text-paper'
                              : dec.decision === 'approved'
                              ? 'bg-signal-gold/15 border-signal-gold/40 text-signal-gold'
                              : 'bg-alert-coral/15 border-alert-coral/40 text-alert-coral'
                          }`}
                        >
                          <span className="pr-2 leading-relaxed">Policy: {dec.reason_text}</span>
                          <span className="font-bold uppercase tracking-wider px-2.5 py-1 rounded bg-ink border border-panel-border shrink-0">
                            {dec.decision}
                          </span>
                        </div>
                      );
                    }

                    return null;
                  })}
                </div>
              )}
            </div>
          );
        })}

        {/* Agent Thinking Indicator */}
        {isThinking && (
          <div className="flex items-center gap-2.5 text-agent-cyan text-xs font-mono p-3 bg-agent-cyan/10 rounded-xl w-fit border border-agent-cyan/30 animate-pulse">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Agent analyzing cart with Groq llama-3.3-70b...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Quick Action Chips */}
      <div className="px-4 py-2.5 border-t border-panel-border/70 bg-ink/70 flex items-center gap-2 overflow-x-auto text-[11px] shrink-0">
        <span className="text-slate font-mono uppercase text-[10px] shrink-0 font-bold">Quick Prompts:</span>
        <button
          onClick={() => handleQuickPrompt("Can you recommend an accessory for my cart?")}
          disabled={isThinking}
          className="px-3 py-1.5 rounded-lg bg-panel border border-panel-border hover:border-agent-cyan text-paper text-xs hover:text-agent-cyan transition-all active:scale-95 shrink-0 whitespace-nowrap shadow-sm disabled:opacity-40"
        >
          ✦ Recommend accessory
        </button>
        <button
          onClick={() => handleQuickPrompt("Can you give me a 35% discount?")}
          disabled={isThinking}
          className="px-3 py-1.5 rounded-lg bg-panel border border-panel-border hover:border-signal-gold text-paper text-xs hover:text-signal-gold transition-all active:scale-95 shrink-0 whitespace-nowrap shadow-sm disabled:opacity-40"
        >
          ⚡ Ask for 35% discount
        </button>
        <button
          onClick={() => handleQuickPrompt("I'm ready to checkout now")}
          disabled={isThinking}
          className="px-3 py-1.5 rounded-lg bg-panel border border-panel-border hover:border-paper text-paper text-xs transition-all active:scale-95 shrink-0 whitespace-nowrap shadow-sm disabled:opacity-40"
        >
          → Ready to checkout
        </button>
        <button
          onClick={handleTriggerStockFailureDemo}
          disabled={isThinking}
          className="px-3 py-1.5 rounded-lg bg-alert-coral/15 border border-alert-coral/40 hover:bg-alert-coral/25 text-alert-coral text-xs font-bold transition-all active:scale-95 shrink-0 whitespace-nowrap shadow-sm disabled:opacity-40 flex items-center gap-1"
          title="Demonstrate TRD.md §9 Option A: Stock Race Condition failure injection"
        >
          <span>⚡ Demo: Stock Race Condition</span>
        </button>
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="p-3 bg-ink border-t border-panel-border flex items-center gap-2.5 shrink-0">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Ask CartMind (e.g. 'Can you suggest an accessory?')..."
          disabled={isThinking}
          className="flex-1 bg-panel border border-panel-border focus:border-agent-cyan rounded-xl px-4 py-3 text-sm text-paper placeholder:text-slate focus:outline-none transition-colors"
        />
        <button
          type="submit"
          disabled={!inputText.trim() || isThinking}
          className="p-3 rounded-xl bg-agent-cyan text-ink font-bold hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-95 shrink-0 shadow-md shadow-agent-cyan/20"
          title="Send message"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
