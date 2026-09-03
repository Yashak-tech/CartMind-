import React from 'react';
import { useCart } from '../context/CartContext';
import { X, Trash2, ShoppingBag, ArrowRight, Sparkles } from 'lucide-react';

export default function CartDrawer() {
  const { cart, isCartOpen, setIsCartOpen, removeFromCart, startCheckout, sendMessage } = useCart();

  if (!isCartOpen) return null;

  const handleAskDiscount = () => {
    setIsCartOpen(false);
    sendMessage("Can you review my cart and see if you can apply a discount?");
  };

  const handleCheckoutClick = () => {
    setIsCartOpen(false);
    startCheckout();
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden animate-fadeIn">
      {/* Backdrop */}
      <div
        onClick={() => setIsCartOpen(false)}
        className="absolute inset-0 bg-ink/75 backdrop-blur-sm transition-opacity"
      />

      {/* Slide-over Drawer overlapping the right rail slightly */}
      <div className="absolute inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md bg-panel border-l border-panel-border shadow-2xl flex flex-col justify-between animate-slideDown">
          {/* Drawer Header */}
          <div className="p-5 border-b border-panel-border flex items-center justify-between bg-ink/60">
            <div className="flex items-center gap-2">
              <ShoppingBag className="w-5 h-5 text-signal-gold" />
              <h2 className="font-display font-bold text-lg text-paper">Your Cart</h2>
              <span className="font-mono text-xs px-2 py-0.5 rounded-full bg-ink border border-panel-border text-slate">
                {cart.total_items} items
              </span>
            </div>
            <button
              onClick={() => setIsCartOpen(false)}
              className="p-1.5 rounded-lg text-slate hover:text-paper hover:bg-ink transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Cart Item List */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {cart.items.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center text-slate space-y-3 p-8">
                <ShoppingBag className="w-12 h-12 stroke-[1.2] text-slate/40" />
                <p className="text-sm font-medium">Your cart is empty</p>
                <p className="text-xs text-slate/70">Explore our curated collection and add items to your cart.</p>
              </div>
            ) : (
              cart.items.map((item) => (
                <div
                  key={item.id}
                  className="bg-ink border border-panel-border rounded-xl p-3 flex gap-3 items-center shadow-sm"
                >
                  <img
                    src={item.image_url}
                    alt={item.name}
                    className="w-16 h-16 object-cover rounded-lg bg-panel shrink-0"
                  />
                  <div className="flex-1 min-w-0">
                    <h4 className="font-display font-bold text-sm text-paper truncate">
                      {item.name}
                    </h4>
                    <p className="font-mono text-xs text-slate">
                      Qty: {item.qty} × ₹{item.price.toFixed(2)}
                    </p>
                    <p className="font-mono text-xs font-bold text-signal-gold mt-1">
                      ₹{item.line_total.toFixed(2)}
                    </p>
                  </div>
                  <button
                    onClick={() => removeFromCart(item.id)}
                    className="p-2 text-slate hover:text-alert-coral hover:bg-panel rounded-lg transition-colors"
                    title="Remove item"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))
            )}
          </div>

          {/* Drawer Footer */}
          {cart.items.length > 0 && (
            <div className="p-5 border-t border-panel-border bg-ink/90 space-y-4">
              <div className="space-y-2 font-mono text-xs">
                <div className="flex justify-between text-slate">
                  <span>Subtotal</span>
                  <span className="text-paper font-semibold">₹{cart.subtotal.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-slate">
                  <span>Estimated Taxes</span>
                  <span className="text-paper font-semibold">Included</span>
                </div>
                <div className="pt-2 border-t border-panel-border flex justify-between text-sm">
                  <span className="font-display font-bold text-paper">Total</span>
                  <span className="font-mono text-base font-bold text-signal-gold">
                    ₹{cart.subtotal.toFixed(2)}
                  </span>
                </div>
              </div>

              {/* Discount prompt action */}
              <button
                onClick={handleAskDiscount}
                className="w-full py-2 px-3 rounded-lg border border-agent-cyan/40 bg-agent-cyan/10 hover:bg-agent-cyan/20 text-agent-cyan font-mono text-xs flex items-center justify-center gap-2 transition-colors"
              >
                <Sparkles className="w-3.5 h-3.5" />
                Ask Agent for Discount Before Checkout
              </button>

              {/* Checkout Button */}
              <button
                onClick={handleCheckoutClick}
                className="w-full py-3 px-4 rounded-xl bg-signal-gold text-ink font-bold text-sm flex items-center justify-center gap-2 hover:opacity-95 shadow-xl transition-opacity"
              >
                Proceed to Checkout
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
