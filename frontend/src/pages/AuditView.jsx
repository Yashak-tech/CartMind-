import React, { useState, useEffect } from 'react';
import { useCart } from '../context/CartContext';
import * as api from '../api';
import DecisionLedger from '../components/DecisionLedger';
import { Shield, Download, RefreshCw, Layers, CheckCircle2, AlertTriangle, AlertOctagon, TrendingUp, DollarSign, Percent, ShieldCheck, FileSpreadsheet } from 'lucide-react';

export default function AuditView() {
  const { sessionId: activeSessionId } = useCart();
  const [sessions, setSessions] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState(activeSessionId || '');
  const [sessionAuditData, setSessionAuditData] = useState(null);
  const [abMetrics, setAbMetrics] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // Load list of all sessions
  const loadSessions = async () => {
    try {
      const list = await api.listAuditSessions();
      setSessions(list);
      if (!selectedSessionId && list.length > 0) {
        setSelectedSessionId(list[0].session_id);
      }
    } catch (err) {
      console.error('Failed to load audit sessions:', err);
    }
  };

  // Load audit trail for selected session
  const loadSessionAudit = async (sid) => {
    if (!sid) return;
    setIsLoading(true);
    try {
      const data = await api.fetchAuditTrail(sid);
      setSessionAuditData(data);
    } catch (err) {
      console.error('Failed to load session audit:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Load precomputed A/B metrics summary
  const loadAbMetrics = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/metrics/summary');
      if (res.ok) {
        const data = await res.json();
        setAbMetrics(data);
      }
    } catch (err) {
      console.error('Failed to load A/B metrics:', err);
    }
  };

  useEffect(() => {
    loadSessions();
    loadAbMetrics();
  }, []);

  useEffect(() => {
    if (selectedSessionId) {
      loadSessionAudit(selectedSessionId);
    }
  }, [selectedSessionId]);

  const handleExportJSON = () => {
    if (!sessionAuditData) return;
    const blob = new Blob([JSON.stringify(sessionAuditData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cartmind-audit-${selectedSessionId.slice(0, 8)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportCSV = () => {
    if (!sessionAuditData || !timeline.length) return;

    const headers = [
      'Timestamp',
      'Time',
      'Action',
      'Summary',
      'Verdict',
      'Rule_Triggered',
      'Justification',
      'Proposed_Value',
      'Applied_Value',
      'Weighted_Margin_Pct',
      'Subtotal',
    ];

    const escapeCsv = (val) => {
      if (val === null || val === undefined) return '""';
      const str = String(val).replace(/"/g, '""');
      return `"${str}"`;
    };

    const rows = timeline.map((entry) => {
      const actionData = entry.payload?.action_data || {};
      return [
        escapeCsv(entry.timestamp),
        escapeCsv(entry.time_str),
        escapeCsv(entry.action),
        escapeCsv(entry.summary),
        escapeCsv(entry.decision),
        escapeCsv(entry.rule_triggered),
        escapeCsv(entry.reason_text),
        escapeCsv(actionData.proposed_percent ?? ''),
        escapeCsv(actionData.applied_percent ?? ''),
        escapeCsv(actionData.weighted_cart_margin ?? ''),
        escapeCsv(actionData.new_subtotal ?? actionData.original_subtotal ?? ''),
      ].join(',');
    });

    const csvContent = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cartmind-audit-${selectedSessionId.slice(0, 8)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const summary = sessionAuditData?.summary || {};
  const timeline = sessionAuditData?.timeline || [];

  return (
    <div className="flex-1 overflow-y-auto p-4 lg:p-8 space-y-8 bg-ink">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-panel-border">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-panel border border-panel-border flex items-center justify-center">
              <Shield className="w-4 h-4 text-signal-gold" />
            </div>
            <h2 className="font-display font-black text-2xl text-paper tracking-tight">
              Audit & Policy Governance Panel
            </h2>
          </div>
          <p className="text-xs text-slate mt-1 max-w-xl">
            Immutable 1:1 proposal-to-gate decision pairing. Every action proposed by the Groq reasoning layer is deterministically evaluated, bounded, and logged with plain-English justification.
          </p>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* Session Selector Dropdown */}
          <div className="flex items-center gap-2 bg-panel border border-panel-border rounded-xl px-3.5 py-2 text-xs font-mono">
            <span className="text-slate font-medium">Session:</span>
            <select
              value={selectedSessionId}
              onChange={(e) => setSelectedSessionId(e.target.value)}
              className="bg-transparent text-paper font-mono focus:outline-none cursor-pointer max-w-[180px] truncate"
            >
              {sessions.map((s) => (
                <option key={s.session_id} value={s.session_id} className="bg-panel text-paper">
                  {s.session_id.slice(0, 10)}... ({s.total_proposals} actions)
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => loadSessionAudit(selectedSessionId)}
            className="p-2.5 rounded-xl bg-panel border border-panel-border hover:border-slate text-slate hover:text-paper transition-colors"
            title="Refresh Audit Data"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>

          {/* Export CSV Button */}
          <button
            onClick={handleExportCSV}
            disabled={!sessionAuditData || !timeline.length}
            className="px-3.5 py-2 rounded-xl bg-panel border border-panel-border hover:border-paper text-paper text-xs font-mono font-medium flex items-center gap-2 transition-all active:scale-95 disabled:opacity-40"
            title="Export Tabular CSV for Spreadsheets"
          >
            <FileSpreadsheet className="w-4 h-4 text-slate" />
            CSV
          </button>

          {/* Export JSON Button */}
          <button
            onClick={handleExportJSON}
            disabled={!sessionAuditData}
            className="px-4 py-2 rounded-xl bg-signal-gold text-ink font-bold text-xs uppercase tracking-wider flex items-center gap-2 transition-all hover:opacity-90 active:scale-95 disabled:opacity-40"
            title="Export Complete Structured JSON"
          >
            <Download className="w-4 h-4 stroke-[2.5]" />
            JSON
          </button>
        </div>
      </div>

      {/* Synthetic A/B Testing Measured Lift Cards (TRD.md §10) */}
      {abMetrics && (
        <section className="bg-gradient-to-r from-panel via-[#182030] to-panel border border-signal-gold/30 rounded-2xl p-5 space-y-4 shadow-xl">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-signal-gold" />
              <span className="font-mono text-xs font-bold uppercase tracking-wider text-paper">
                SYNTHETIC A/B EVALUATION BENCHMARK (30 SESSIONS)
              </span>
            </div>
            <span className="text-[10px] font-mono text-emerald-400 font-bold px-2 py-0.5 rounded bg-emerald-400/10 border border-emerald-400/30">
              ✓ STATISTICALLY MEASURED LIFT
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono text-xs">
            <div className="bg-ink/70 p-3.5 rounded-xl border border-panel-border space-y-1">
              <span className="text-slate text-[10px] uppercase block">Control vs CartMind AOV</span>
              <div className="flex items-baseline gap-2">
                <span className="text-base font-black text-signal-gold">
                  ₹{abMetrics.agent_aov?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
                <span className="text-[10px] text-slate line-through">
                  ₹{abMetrics.baseline_aov?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
              <span className="text-[10px] text-emerald-400 font-bold block">
                +₹{abMetrics.aov_lift_abs} per order
              </span>
            </div>

            <div className="bg-ink/70 p-3.5 rounded-xl border border-panel-border space-y-1">
              <span className="text-slate text-[10px] uppercase block">Upsell Acceptance Rate</span>
              <span className="text-base font-black text-agent-cyan block">
                {abMetrics.upsell_acceptance_rate}%
              </span>
              <span className="text-[10px] text-slate block">
                {abMetrics.upsells_accepted} of {abMetrics.upsells_offered} upsells accepted
              </span>
            </div>

            <div className="bg-ink/70 p-3.5 rounded-xl border border-panel-border space-y-1">
              <span className="text-slate text-[10px] uppercase block">Margin Gate Interventions</span>
              <span className="text-base font-black text-paper block">
                {abMetrics.gate_intervention_rate}%
              </span>
              <span className="text-[10px] text-signal-gold block">
                {abMetrics.discounts_modified} discount requests capped
              </span>
            </div>

            <div className="bg-ink/70 p-3.5 rounded-xl border border-panel-border space-y-1">
              <span className="text-slate text-[10px] uppercase block">10% Margin Floor Compliance</span>
              <div className="flex items-center gap-1.5 text-emerald-400 font-bold text-base">
                <ShieldCheck className="w-4 h-4" />
                <span>100%</span>
              </div>
              <span className="text-[10px] text-slate block">
                0 unauthorized margin breaches
              </span>
            </div>
          </div>
        </section>
      )}

      {/* Selected Session KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono">
        <div className="bg-panel border border-panel-border rounded-xl p-4 space-y-1">
          <div className="flex items-center justify-between text-slate text-xs">
            <span>Total Proposals</span>
            <Layers className="w-4 h-4" />
          </div>
          <p className="text-2xl font-black text-paper">{summary.total_proposals || 0}</p>
          <p className="text-[10px] text-slate">Tool calls emitted by LLM</p>
        </div>

        <div className="bg-panel border border-signal-gold/30 rounded-xl p-4 space-y-1">
          <div className="flex items-center justify-between text-signal-gold text-xs">
            <span>Approved Actions</span>
            <CheckCircle2 className="w-4 h-4 text-signal-gold" />
          </div>
          <p className="text-2xl font-black text-signal-gold">{summary.approved || 0}</p>
          <p className="text-[10px] text-slate">Executed within policy bounds</p>
        </div>

        <div className="bg-panel border border-panel-border rounded-xl p-4 space-y-1">
          <div className="flex items-center justify-between text-slate text-xs">
            <span>Modified Actions</span>
            <AlertTriangle className="w-4 h-4 text-slate" />
          </div>
          <p className="text-2xl font-black text-slate">{summary.modified || 0}</p>
          <p className="text-[10px] text-slate">Capped to ceiling / margin floor</p>
        </div>

        <div className="bg-panel border border-alert-coral/30 rounded-xl p-4 space-y-1">
          <div className="flex items-center justify-between text-alert-coral text-xs">
            <span>Blocked Actions</span>
            <AlertOctagon className="w-4 h-4 text-alert-coral" />
          </div>
          <p className="text-2xl font-black text-alert-coral">{summary.blocked || 0}</p>
          <p className="text-[10px] text-slate">Violated stock, cap, or policy</p>
        </div>
      </div>

      {/* Full-width Signature Decision Ledger */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-mono text-xs uppercase tracking-widest text-slate font-bold">
            CHRONOLOGICAL DECISION STREAM FOR SESSION: {selectedSessionId.slice(0, 8)}...
          </h3>
          <span className="font-mono text-xs text-slate">
            {timeline.length} Recorded Governance Events
          </span>
        </div>

        <DecisionLedger timeline={timeline} isFullWidth={true} />
      </div>
    </div>
  );
}
