import React from 'react';
import { useCart } from '../context/CartContext';
import { ShoppingBag, RefreshCw, Shield, ArrowLeft, Flame, Sparkles } from 'lucide-react';

export default function Header({ currentView, setCurrentView }) {
  const { cart, setIsCartOpen, sessionId, resetSession } = useCart();

  return (
    <div className="shrink-0 flex flex-col z-40 bg-ink">
      {/* Top Luxury Announcement Ribbon inspired by SoleDistrict */}
      <div className="bg-[#18110B] border-b border-signal-gold/20 px-4 py-1.5 text-[11px] font-mono text-[#D4A373] flex items-center justify-between overflow-x-auto whitespace-nowrap">
        <div className="flex items-center gap-4 mx-auto">
          <span className="flex items-center gap-1.5 font-semibold text-signal-gold">
            <span className="w-1.5 h-1.5 rounded-full bg-signal-gold animate-ping inline-block"></span>
            RAZORPAY TEST MODE ACTIVE
          </span>
          <span className="text-slate/60">•</span>
          <span>10% HARD MARGIN FLOOR PROTECTION</span>
          <span className="text-slate/60">•</span>
          <span className="text-paper/80">ALL AGENT ACTIONS DETERMINISTICALLY GATED</span>
          <span className="text-slate/60">•</span>
          <span className="text-signal-gold font-medium">FREE DISPATCH OVER ₹999</span>
        </div>
      </div>

      {/* Main Navbar */}
      <header className="h-16 px-4 lg:px-8 bg-panel/95 border-b border-panel-border backdrop-blur-md flex items-center justify-between">
        {/* Brand & Wordmark */}
        <div className="flex items-center gap-6">
          <div
            onClick={() => setCurrentView('shop')}
            className="flex items-center gap-3 cursor-pointer select-none group"
          >
            <div className="w-9 h-9 rounded-xl bg-ink border border-panel-border flex items-center justify-center group-hover:border-signal-gold transition-colors shadow-inner">
              <span className="w-4 h-4 rounded bg-gradient-to-br from-signal-gold to-[#B8860B] inline-block shadow-sm"></span>
            </div>
            <div>
              <h1 className="font-display font-black text-2xl tracking-tighter text-paper leading-none">
                CART<span className="text-signal-gold">MIND</span>
              </h1>
              <p className="text-[9px] font-mono tracking-widest text-slate uppercase leading-none mt-1">
                Accountable AI Commerce
              </p>
            </div>
          </div>

          {/* Quick Navigation Links */}
          <nav className="hidden md:flex items-center gap-1 text-xs font-mono">
            <button
              onClick={() => setCurrentView('shop')}
              className={`px-3 py-1.5 rounded-lg transition-colors ${
                currentView === 'shop'
                  ? 'text-signal-gold font-bold bg-ink border border-panel-border'
                  : 'text-slate hover:text-paper'
              }`}
            >
              Curated Catalog
            </button>
            <button
              onClick={() => setCurrentView('audit')}
              className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors ${
                currentView === 'audit'
                  ? 'text-signal-gold font-bold bg-ink border border-panel-border'
                  : 'text-slate hover:text-paper'
              }`}
            >
              <Shield className="w-3.5 h-3.5 text-signal-gold" />
              Decision Audit
            </button>
          </nav>
        </div>

        {/* Center/Right Session & Actions */}
        <div className="flex items-center gap-3">
          {/* Active Session Pill */}
          {sessionId && (
            <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-ink border border-panel-border text-[11px] font-mono text-slate">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span>Session:</span>
              <span className="text-paper font-semibold">{sessionId.slice(0, 8)}...</span>
            </div>
          )}

          {/* New Session Refresh */}
          <button
            onClick={resetSession}
            title="Start fresh session"
            className="p-2.5 rounded-xl bg-ink border border-panel-border text-slate hover:text-paper hover:border-slate transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          {/* Cart Trigger */}
          <button
            onClick={() => setIsCartOpen(true)}
            className="relative px-4 py-2 rounded-xl bg-signal-gold text-ink font-bold text-xs flex items-center gap-2.5 hover:opacity-90 active:scale-95 transition-all shadow-md shadow-signal-gold/10"
          >
            <ShoppingBag className="w-4 h-4" />
            <span className="font-semibold uppercase tracking-wider text-[11px]">Cart</span>
            {cart.total_items > 0 ? (
              <span className="px-1.5 py-0.2 rounded-full bg-ink text-paper font-mono text-[11px] font-bold">
                {cart.total_items}
              </span>
            ) : (
              <span className="text-ink/60 font-mono text-xs">0</span>
            )}
          </button>
        </div>
      </header>
    </div>
  );
}
