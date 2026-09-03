import React, { useState } from 'react';
import ChatPanel from './ChatPanel';
import DecisionLedger from './DecisionLedger';
import { useCart } from '../context/CartContext';
import { Bot, Terminal, Shield, ChevronUp } from 'lucide-react';

/**
 * Agent Rail (~40% width on desktop).
 * Provides generous, beautiful space for the AI Chatbot with interactive view switching:
 *   - Tab 1: AI Assistant (Full-height conversation experience with live mini-ticker)
 *   - Tab 2: Decision Ledger (Detailed monospace rule audit stream)
 */
export default function AgentRail() {
  const { auditFeed } = useCart();
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'ledger'

  const approvedCount = auditFeed.filter(e => e.decision === 'approved').length;
  const modifiedCount = auditFeed.filter(e => e.decision === 'modified').length;
  const blockedCount = auditFeed.filter(e => e.decision === 'blocked').length;

  // Latest decision for live mini-ticker at bottom of chat
  const latestDecision = auditFeed[0];

  return (
    <aside className="w-full h-full flex flex-col bg-ink overflow-hidden">
      {/* Top Agent Rail Tab Bar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-panel border-b border-panel-border shrink-0">
        <div className="flex items-center gap-1.5 p-1 bg-ink rounded-xl border border-panel-border text-xs font-mono">
          <button
            onClick={() => setActiveTab('chat')}
            className={`px-3.5 py-1.5 rounded-lg flex items-center gap-2 font-bold transition-all ${
              activeTab === 'chat'
                ? 'bg-agent-cyan text-ink shadow-md shadow-agent-cyan/20'
                : 'text-slate hover:text-paper'
            }`}
          >
            <Bot className="w-4 h-4" />
            <span>AI Copilot</span>
          </button>

          <button
            onClick={() => setActiveTab('ledger')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-2 font-bold transition-all ${
              activeTab === 'ledger'
                ? 'bg-signal-gold text-ink shadow-md shadow-signal-gold/20'
                : 'text-slate hover:text-paper'
            }`}
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>Decision Ledger</span>
            {auditFeed.length > 0 && (
              <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
                activeTab === 'ledger' ? 'bg-ink text-paper' : 'bg-signal-gold/20 text-signal-gold'
              }`}>
                {auditFeed.length}
              </span>
            )}
          </button>
        </div>

        {/* Live Status Indicator */}
        <div className="hidden sm:flex items-center gap-2 font-mono text-[11px] text-slate">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>GATING ACTIVE</span>
        </div>
      </div>

      {/* Main Tab Content */}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden p-3">
        {activeTab === 'chat' ? (
          <div className="flex-1 flex flex-col min-h-0 gap-2.5 overflow-hidden">
            {/* Full-Height Chatbot Panel */}
            <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
              <ChatPanel />
            </div>

            {/* Live Monospace Mini-Ticker docked below Chat */}
            {latestDecision && (
              <div
                onClick={() => setActiveTab('ledger')}
                className="shrink-0 bg-panel border border-panel-border hover:border-signal-gold/50 rounded-xl px-3.5 py-2 flex items-center justify-between gap-2 font-mono text-[11px] cursor-pointer transition-all shadow-md group"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-signal-gold font-bold shrink-0">&gt;_</span>
                  <span className="text-slate shrink-0">{latestDecision.time_str}</span>
                  <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold uppercase shrink-0 ${
                    latestDecision.decision === 'approved'
                      ? 'bg-signal-gold/20 text-signal-gold border border-signal-gold/40'
                      : latestDecision.decision === 'blocked'
                      ? 'bg-alert-coral/20 text-alert-coral border border-alert-coral/40'
                      : 'bg-slate/25 text-slate border border-slate/40'
                  }`}>
                    {latestDecision.decision}
                  </span>
                  <span className="truncate text-paper text-xs" title={latestDecision.summary}>
                    {latestDecision.summary}
                  </span>
                </div>
                <div className="flex items-center gap-1 text-signal-gold text-[10px] font-bold uppercase shrink-0 group-hover:underline">
                  <span>Ledger</span>
                  <ChevronUp className="w-3.5 h-3.5 rotate-90" />
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Full Decision Ledger View */
          <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
            <DecisionLedger timeline={auditFeed} isFullWidth={true} />
          </div>
        )}
      </div>
    </aside>
  );
}
