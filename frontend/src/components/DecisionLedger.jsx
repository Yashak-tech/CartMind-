import React, { useState } from 'react';
import { Terminal, Shield, ChevronDown, ChevronUp, Sliders } from 'lucide-react';

/**
 * Decision Ledger Component (FRONTEND_PROMPT.md Signature Element).
 * Monospace live ticker rendering gate decisions in real time.
 * Color-coded:
 *   - signal-gold (#E8B84F) for approved
 *   - alert-coral (#E8614F) for blocked
 *   - slate (#566073) for modified
 */
export default function DecisionLedger({ timeline = [], isFullWidth = false }) {
  const [expandedId, setExpandedId] = useState(null);

  const toggleExpand = (id) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className={`bg-panel border border-panel-border rounded-2xl flex flex-col ${isFullWidth ? 'w-full shadow-2xl' : 'h-72'} overflow-hidden shadow-xl`}>
      {/* Header bar styled like an accountability trading terminal */}
      <div className="bg-ink/90 px-4 py-3 border-b border-panel-border flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded-md bg-panel border border-panel-border flex items-center justify-center">
            <Terminal className="w-3.5 h-3.5 text-signal-gold" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold tracking-wider uppercase text-paper">
                DECISION LEDGER
              </span>
              <span className="inline-flex items-center px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-signal-gold/15 text-signal-gold border border-signal-gold/30">
                LIVE
              </span>
            </div>
            <p className="text-[10px] font-mono text-slate">Deterministic Rule Audit Stream</p>
          </div>
        </div>

        {/* Ticker KPI Badges */}
        <div className="flex items-center gap-2.5 font-mono text-[11px]">
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-ink border border-signal-gold/30 text-signal-gold font-bold">
            <span className="w-1.5 h-1.5 rounded-full bg-signal-gold"></span>
            APP: {timeline.filter(e => e.decision === 'approved').length}
          </span>
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-ink border border-slate/30 text-slate font-bold">
            <span className="w-1.5 h-1.5 rounded-full bg-slate"></span>
            MOD: {timeline.filter(e => e.decision === 'modified').length}
          </span>
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-ink border border-alert-coral/30 text-alert-coral font-bold">
            <span className="w-1.5 h-1.5 rounded-full bg-alert-coral"></span>
            BLK: {timeline.filter(e => e.decision === 'blocked').length}
          </span>
        </div>
      </div>

      {/* Ledger Feed */}
      <div className="flex-1 overflow-y-auto p-2.5 space-y-2 font-mono text-xs selection:bg-slate/30">
        {timeline.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate text-center p-6 space-y-2">
            <Sliders className="w-6 h-6 stroke-[1.5] text-slate/40" />
            <p className="text-xs font-medium text-paper">Awaiting agent proposals...</p>
            <p className="text-[11px] text-slate/70 max-w-xs">
              When the AI proposes an action (recommendation, discount, checkout), the deterministic Gating Engine evaluates and logs its verdict here.
            </p>
          </div>
        ) : (
          timeline.map((entry) => {
            const isApproved = entry.decision === 'approved';
            const isBlocked = entry.decision === 'blocked';
            const isModified = entry.decision === 'modified';
            const isExpanded = expandedId === entry.id;

            // Border & Accent mapping per design tokens
            let rowColor = 'text-paper border-panel-border hover:border-slate/50 bg-ink/40';
            let badgeStyle = 'bg-slate/15 text-slate border-slate/40';
            let verdictSymbol = 'ℹ';

            if (isApproved) {
              rowColor = 'text-paper border-signal-gold/40 hover:border-signal-gold/70 bg-signal-gold/[0.03]';
              badgeStyle = 'bg-signal-gold/15 text-signal-gold border-signal-gold/50';
              verdictSymbol = '✓';
            } else if (isBlocked) {
              rowColor = 'text-paper border-alert-coral/40 hover:border-alert-coral/70 bg-alert-coral/[0.03]';
              badgeStyle = 'bg-alert-coral/15 text-alert-coral border-alert-coral/50';
              verdictSymbol = '✕';
            } else if (isModified) {
              rowColor = 'text-paper border-slate/40 hover:border-slate/70 bg-slate/[0.05]';
              badgeStyle = 'bg-slate/25 text-slate border-slate/50';
              verdictSymbol = '◐';
            }

            return (
              <div
                key={entry.id}
                className={`rounded-xl border transition-all duration-150 animate-slideDown overflow-hidden ${rowColor}`}
              >
                <div
                  onClick={() => toggleExpand(entry.id)}
                  className="px-3.5 py-2.5 flex items-center justify-between gap-3 cursor-pointer select-none"
                >
                  {/* Left: Time & Action & Target */}
                  <div className="flex items-center gap-2.5 min-w-0 flex-1">
                    <span className="text-slate text-[11px] font-semibold shrink-0">
                      {entry.time_str || '00:00:00'}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase shrink-0 bg-ink border border-panel-border text-paper">
                      {entry.action}
                    </span>
                    <span className="truncate text-paper text-xs font-medium" title={entry.summary}>
                      {entry.summary}
                    </span>
                  </div>

                  {/* Right: Decision Tag */}
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border flex items-center gap-1.5 shadow-sm ${badgeStyle}`}>
                      <span className="font-mono">{verdictSymbol}</span>
                      <span className="uppercase tracking-wider">{entry.decision}</span>
                    </span>
                    {isExpanded ? (
                      <ChevronUp className="w-3.5 h-3.5 text-slate" />
                    ) : (
                      <ChevronDown className="w-3.5 h-3.5 text-slate" />
                    )}
                  </div>
                </div>

                {/* Expanded Detail Drawer */}
                {isExpanded && (
                  <div className="px-4 py-3 border-t border-panel-border/60 text-[11px] text-paper/90 bg-ink/70 space-y-2">
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <div className="flex items-center gap-2">
                        <span className="text-slate font-medium">Rule Triggered:</span>
                        <code className="text-signal-gold bg-panel px-2 py-0.5 rounded border border-panel-border text-[10px] font-bold">
                          {entry.rule_triggered || 'standard_rule'}
                        </code>
                      </div>
                      {entry.payload && entry.payload.recommendation_id && (
                        <span className="text-slate text-[10px]">
                          Audit Ref #{entry.payload.recommendation_id}
                        </span>
                      )}
                    </div>
                    <div>
                      <span className="text-slate font-medium">Justification: </span>
                      <span className="text-paper">{entry.reason_text}</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
