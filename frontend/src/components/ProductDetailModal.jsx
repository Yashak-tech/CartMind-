import React, { useState } from 'react';
import { useCart } from '../context/CartContext';
import { X, Plus, Check, Loader2, Sparkles, ShieldCheck } from 'lucide-react';

export default function ProductDetailModal({ product, onClose }) {
  const { addToCart, sendMessage } = useCart();
  const [qty, setQty] = useState(1);
  const [isAdding, setIsAdding] = useState(false);
  const [justAdded, setJustAdded] = useState(false);

  if (!product) return null;

  const isLowStock = product.stock_qty <= 2 && product.stock_qty > 0;
  const isOutOfStock = product.stock_qty <= 0;

  const handleAdd = async () => {
    if (isOutOfStock || isAdding) return;
    setIsAdding(true);
    const res = await addToCart(product.id, qty);
    setIsAdding(false);
    if (res.success) {
      setJustAdded(true);
      // Contextually inform agent rail
      sendMessage(`I just added the ${product.name} to my cart.`);
      setTimeout(() => {
        setJustAdded(false);
        onClose();
      }, 800);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/80 backdrop-blur-sm animate-fadeIn">
      <div className="bg-panel border border-panel-border rounded-2xl max-w-2xl w-full overflow-hidden shadow-2xl flex flex-col md:flex-row">
        {/* Left Image */}
        <div className="md:w-1/2 relative bg-ink aspect-square md:aspect-auto">
          <img
            src={product.image_url}
            alt={product.name}
            className="w-full h-full object-cover"
          />
          <div className="absolute top-4 left-4">
            <span className="px-2.5 py-1 rounded-md text-[11px] font-mono uppercase bg-ink/90 text-paper border border-panel-border">
              {product.category}
            </span>
          </div>
        </div>

        {/* Right Details */}
        <div className="md:w-1/2 p-6 flex flex-col justify-between space-y-6">
          <div className="space-y-3">
            <div className="flex items-start justify-between">
              <h2 className="font-display font-bold text-xl text-paper leading-tight">
                {product.name}
              </h2>
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg text-slate hover:text-paper hover:bg-ink transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex items-center gap-3">
              <span className="font-mono text-xl font-bold text-signal-gold">
                ₹{product.price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </span>

              {isOutOfStock ? (
                <span className="px-2 py-0.5 rounded text-[11px] font-mono uppercase bg-alert-coral/20 text-alert-coral border border-alert-coral">
                  Out of Stock
                </span>
              ) : isLowStock ? (
                <span className="px-2 py-0.5 rounded text-[11px] font-mono uppercase bg-alert-coral/10 text-alert-coral border border-alert-coral animate-pulse">
                  Only {product.stock_qty} Units Remaining
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded text-[11px] font-mono uppercase bg-ink text-slate border border-slate/40">
                  {product.stock_qty} in stock
                </span>
              )}
            </div>

            <p className="text-sm text-slate leading-relaxed pt-2">
              {product.description}
            </p>

            <div className="pt-2 text-xs text-slate space-y-1.5 font-mono">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-signal-gold" />
                <span>Verified Stock & Authentic Gear</span>
              </div>
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-agent-cyan" />
                <span>Eligible for Agent Bundling & Dynamic Incentives</span>
              </div>
            </div>
          </div>

          <div className="space-y-4 pt-4 border-t border-panel-border">
            <div className="flex items-center gap-4">
              <div className="flex items-center border border-panel-border rounded-lg bg-ink">
                <button
                  onClick={() => setQty(Math.max(1, qty - 1))}
                  disabled={qty <= 1}
                  className="px-3 py-1.5 text-paper hover:bg-panel disabled:opacity-30"
                >
                  -
                </button>
                <span className="font-mono text-sm px-3">{qty}</span>
                <button
                  onClick={() => setQty(Math.min(product.stock_qty, qty + 1))}
                  disabled={qty >= product.stock_qty}
                  className="px-3 py-1.5 text-paper hover:bg-panel disabled:opacity-30"
                >
                  +
                </button>
              </div>

              <button
                onClick={handleAdd}
                disabled={isOutOfStock || isAdding}
                className={`flex-1 py-3 px-4 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 transition-all ${
                  justAdded
                    ? 'bg-signal-gold text-ink'
                    : isOutOfStock
                    ? 'bg-ink border border-panel-border text-slate cursor-not-allowed'
                    : 'bg-signal-gold text-ink hover:opacity-90 shadow-lg'
                }`}
              >
                {isAdding ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : justAdded ? (
                  <>
                    <Check className="w-4 h-4" />
                    Added to Cart
                  </>
                ) : (
                  <>
                    <Plus className="w-4 h-4" />
                    Add to Cart • ₹{(product.price * qty).toFixed(2)}
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
