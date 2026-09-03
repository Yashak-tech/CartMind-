import React, { useState } from 'react';
import { useCart } from '../context/CartContext';
import ProductCard from './ProductCard';
import ProductDetailModal from './ProductDetailModal';
import { Filter, Sparkles, AlertCircle, ShoppingBag, ShieldCheck, Zap, Lock, Headphones, Watch, Laptop } from 'lucide-react';

export default function Storefront() {
  const { products, isLoadingProducts, errorMessage, setErrorMessage } = useCart();
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [activeModalProduct, setActiveModalProduct] = useState(null);

  const categories = [
    { id: 'All', label: 'All Gear', icon: Sparkles },
    { id: 'Audio & Tech', label: 'Audio & Tech', icon: Headphones },
    { id: 'Everyday Carry', label: 'Everyday Carry', icon: Watch },
    { id: 'Workspace & Productivity', label: 'Workspace', icon: Laptop },
  ];

  const filteredProducts = selectedCategory === 'All'
    ? products
    : products.filter(p => (
        p.category.toLowerCase().includes(selectedCategory.toLowerCase()) ||
        selectedCategory.toLowerCase().includes(p.category.toLowerCase())
      ));

  return (
    <main className="flex-1 overflow-y-auto p-4 lg:p-7 space-y-8 bg-ink">
      {/* Error alert if any */}
      {errorMessage && (
        <div className="bg-alert-coral/15 border border-alert-coral/40 rounded-xl p-3.5 flex items-center justify-between text-xs text-alert-coral animate-fadeIn">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-paper hover:underline font-mono"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Hero Banner inspired by SoleDistrict Editorial Layout */}
      <section className="relative rounded-3xl bg-gradient-to-br from-[#1A1410] via-panel to-ink border border-panel-border p-6 lg:p-10 overflow-hidden shadow-2xl">
        {/* Subtle background ambient glow */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-signal-gold/5 rounded-full blur-3xl pointer-events-none"></div>

        <div className="relative z-10 max-w-2xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono font-medium bg-signal-gold/10 text-signal-gold border border-signal-gold/30">
            <Sparkles className="w-3.5 h-3.5" />
            <span>CURATED TECH & EVERYDAY CARRY</span>
          </div>

          <h2 className="font-display font-black text-3xl sm:text-4xl lg:text-5xl text-paper tracking-tight leading-[1.1]">
            ENGINEERED ESSENTIALS.<br />
            <span className="text-signal-gold">BOUNDED BY DESIGN.</span>
          </h2>

          <p className="text-sm text-slate leading-relaxed max-w-lg">
            High-performance audio, EDC gear, and workspace tools. Every recommendation, discount, and payment action proposed by our AI is deterministically validated before execution.
          </p>

          {/* Value Props Row */}
          <div className="pt-2 flex items-center gap-4 flex-wrap text-xs font-mono text-paper/80">
            <div className="flex items-center gap-1.5 bg-ink/70 px-3 py-1.5 rounded-lg border border-panel-border">
              <ShieldCheck className="w-4 h-4 text-signal-gold" />
              <span>10% Hard Margin Floor</span>
            </div>
            <div className="flex items-center gap-1.5 bg-ink/70 px-3 py-1.5 rounded-lg border border-panel-border">
              <Lock className="w-4 h-4 text-emerald-400" />
              <span>Zero Hallucinated Discounts</span>
            </div>
            <div className="flex items-center gap-1.5 bg-ink/70 px-3 py-1.5 rounded-lg border border-panel-border">
              <Zap className="w-4 h-4 text-agent-cyan" />
              <span>Razorpay Verified</span>
            </div>
          </div>
        </div>
      </section>

      {/* Category Navigation Pills inspired by SoleDistrict */}
      <div className="space-y-4">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <span className="text-[10px] font-mono uppercase tracking-widest text-slate block mb-1">
              EXPLORE COLLECTION
            </span>
            <div className="flex items-center gap-2 flex-wrap">
              {categories.map((cat) => {
                const Icon = cat.icon;
                const isActive = selectedCategory === cat.id;
                return (
                  <button
                    key={cat.id}
                    onClick={() => setSelectedCategory(cat.id)}
                    className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all ${
                      isActive
                        ? 'bg-signal-gold text-ink shadow-md font-bold'
                        : 'bg-panel text-slate hover:text-paper hover:border-slate border border-panel-border'
                    }`}
                  >
                    <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-ink' : 'text-slate'}`} />
                    <span>{cat.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="font-mono text-xs text-slate">
            Showing <span className="text-signal-gold font-bold">{filteredProducts.length}</span> curated items
          </div>
        </div>

        {/* 3-Column Responsive Product Grid */}
        {isLoadingProducts ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
            {[1, 2, 3, 4, 5, 6].map((n) => (
              <div key={n} className="bg-panel border border-panel-border rounded-2xl aspect-[3/4] animate-pulse"></div>
            ))}
          </div>
        ) : filteredProducts.length === 0 ? (
          <div className="p-16 text-center text-slate space-y-3 bg-panel border border-panel-border rounded-2xl">
            <ShoppingBag className="w-10 h-10 mx-auto stroke-[1.2] text-slate/40" />
            <p className="text-sm font-medium">No items found in this category.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
            {filteredProducts.map((product) => (
              <ProductCard
                key={product.id}
                product={product}
                onSelect={(p) => setActiveModalProduct(p)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Brand Trust Section inspired by SoleDistrict "MORE THAN A BRAND" */}
      <section className="mt-12 rounded-2xl bg-panel border border-panel-border p-6 lg:p-8 space-y-6">
        <div className="max-w-xl">
          <span className="text-[10px] font-mono text-signal-gold uppercase tracking-widest block mb-1">
            ARCHITECTURE OF TRUST
          </span>
          <h3 className="font-display font-bold text-xl text-paper">
            Why CartMind Gated Commerce?
          </h3>
          <p className="text-xs text-slate mt-1">
            Unlike chatbots that hallucinate promises or write directly to databases, CartMind enforces strict policy boundaries at the server level.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
          <div className="bg-ink p-4 rounded-xl border border-panel-border space-y-2">
            <div className="text-signal-gold font-bold">01. MARGIN FLOOR</div>
            <p className="text-slate text-[11px] leading-relaxed">
              Every discount calculation computes the cart's revenue-weighted margin to ensure profit never falls below 10%.
            </p>
          </div>
          <div className="bg-ink p-4 rounded-xl border border-panel-border space-y-2">
            <div className="text-agent-cyan font-bold">02. SEPARATE ENGINE</div>
            <p className="text-slate text-[11px] leading-relaxed">
              The LLM reasoning layer has zero database write access. It proposes actions; our pure-Python gate decides.
            </p>
          </div>
          <div className="bg-ink p-4 rounded-xl border border-panel-border space-y-2">
            <div className="text-emerald-400 font-bold">03. AUDIT REPRODUCIBILITY</div>
            <p className="text-slate text-[11px] leading-relaxed">
              Every proposal and decision produces an immutable audit record with plain-English justification.
            </p>
          </div>
        </div>
      </section>

      {/* Product Detail Modal */}
      {activeModalProduct && (
        <ProductDetailModal
          product={activeModalProduct}
          onClose={() => setActiveModalProduct(null)}
        />
      )}
    </main>
  );
}
