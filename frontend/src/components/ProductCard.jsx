import React, { useState } from 'react';
import { useCart } from '../context/CartContext';
import { Plus, Check, Loader2, Heart } from 'lucide-react';

export default function ProductCard({ product, onSelect }) {
  const { addToCart } = useCart();
  const [isAdding, setIsAdding] = useState(false);
  const [justAdded, setJustAdded] = useState(false);
  const [isFavorited, setIsFavorited] = useState(false);

  const isLowStock = product.stock_qty <= 2 && product.stock_qty > 0;
  const isOutOfStock = product.stock_qty <= 0;

  const handleQuickAdd = async (e) => {
    e.stopPropagation();
    if (isOutOfStock || isAdding) return;
    setIsAdding(true);
    const result = await addToCart(product.id, 1);
    setIsAdding(false);
    if (result.success) {
      setJustAdded(true);
      setTimeout(() => setJustAdded(false), 1400);
    }
  };

  const handleToggleFavorite = (e) => {
    e.stopPropagation();
    setIsFavorited(!isFavorited);
  };

  return (
    <div
      onClick={() => onSelect(product)}
      className="group bg-panel border border-panel-border hover:border-slate/70 rounded-2xl overflow-hidden flex flex-col transition-all duration-300 cursor-pointer shadow-md hover:shadow-2xl hover:-translate-y-1"
    >
      {/* Product Image Area */}
      <div className="relative aspect-[4/3] bg-ink overflow-hidden">
        <img
          src={product.image_url}
          alt={product.name}
          className="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-500 ease-out"
          loading="lazy"
        />

        {/* Top Floating Badges */}
        <div className="absolute top-3 inset-x-3 flex items-center justify-between pointer-events-none">
          {/* Stock Pill per FRONTEND_PROMPT.md */}
          {isOutOfStock ? (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold tracking-wider uppercase bg-alert-coral/20 text-alert-coral border border-alert-coral backdrop-blur-md">
              OUT OF STOCK
            </span>
          ) : isLowStock ? (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold tracking-wider uppercase bg-alert-coral/20 text-alert-coral border border-alert-coral backdrop-blur-md animate-pulse">
              ONLY {product.stock_qty} LEFT
            </span>
          ) : (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-mono font-medium tracking-wider uppercase bg-ink/80 text-slate border border-slate/40 backdrop-blur-md">
              IN STOCK ({product.stock_qty})
            </span>
          )}

          {/* Wishlist Heart Icon inspired by SoleDistrict */}
          <button
            onClick={handleToggleFavorite}
            className="w-8 h-8 rounded-full bg-ink/80 hover:bg-ink border border-panel-border flex items-center justify-center text-slate hover:text-signal-gold transition-colors pointer-events-auto backdrop-blur-md"
            title="Add to Wishlist"
          >
            <Heart className={`w-4 h-4 ${isFavorited ? 'fill-signal-gold text-signal-gold' : ''}`} />
          </button>
        </div>

        {/* Category Pill */}
        <div className="absolute bottom-3 left-3">
          <span className="px-2.5 py-0.5 rounded-md text-[10px] font-mono uppercase tracking-wider bg-ink/90 text-paper/90 border border-panel-border backdrop-blur-md">
            {product.category}
          </span>
        </div>
      </div>

      {/* Product Info Area */}
      <div className="p-4 sm:p-5 flex-1 flex flex-col justify-between space-y-4">
        <div className="space-y-1">
          <span className="text-[10px] font-mono tracking-widest text-slate uppercase block">
            CARTMIND DROP
          </span>
          <h3 className="font-display font-bold text-base text-paper group-hover:text-signal-gold transition-colors leading-snug line-clamp-1">
            {product.name}
          </h3>
          <p className="text-xs text-slate line-clamp-2 leading-relaxed pt-0.5">
            {product.description}
          </p>
        </div>

        {/* Price & Action Button */}
        <div className="pt-3 border-t border-panel-border/60 flex items-center justify-between gap-2">
          <div>
            <span className="text-[10px] font-mono uppercase text-slate block leading-none mb-1">
              PRICE
            </span>
            <span className="font-mono text-base sm:text-lg font-black text-signal-gold leading-none">
              ₹{product.price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </span>
          </div>

          <button
            onClick={handleQuickAdd}
            disabled={isOutOfStock || isAdding}
            className={`px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 transition-all active:scale-95 ${
              justAdded
                ? 'bg-signal-gold text-ink shadow-md'
                : isOutOfStock
                ? 'bg-ink border border-panel-border text-slate cursor-not-allowed opacity-40'
                : 'bg-signal-gold text-ink hover:opacity-90 shadow-md shadow-signal-gold/10'
            }`}
          >
            {isAdding ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : justAdded ? (
              <>
                <Check className="w-3.5 h-3.5 stroke-[2.5]" />
                Added
              </>
            ) : (
              <>
                <Plus className="w-3.5 h-3.5 stroke-[2.5]" />
                Add
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
