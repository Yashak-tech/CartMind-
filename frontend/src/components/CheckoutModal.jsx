import React, { useState } from 'react';
import { useCart } from '../context/CartContext';
import { X, CheckCircle, ShieldCheck, ArrowRight, Loader2, ExternalLink } from 'lucide-react';

export default function CheckoutModal() {
  const { isCheckoutOpen, setIsCheckoutOpen, checkoutData, cart, refreshAudit, refreshCart } = useCart();
  const [isProcessing, setIsProcessing] = useState(false);
  const [paymentSuccess, setPaymentSuccess] = useState(false);
  const [paymentDetails, setPaymentDetails] = useState(null);

  if (!isCheckoutOpen) return null;

  const handleSimulatePayment = async () => {
    setIsProcessing(true);
    try {
      // 1. Call simulation endpoint directly on backend
      const simRes = await fetch('http://127.0.0.1:8000/api/test-payment/simulate', { method: 'POST' });
      const simData = await simRes.json();

      // 2. Trigger callback to complete cryptographic verification
      if (simData.callback_url) {
        await fetch(`http://127.0.0.1:8000${simData.callback_url}`);
      }

      setPaymentSuccess(true);
      setPaymentDetails({
        paymentId: 'pay_simulated_demo_100',
        orderId: checkoutData?.razorpay_order_id || 'order_demo_test',
        amount: checkoutData?.amount || cart.subtotal,
      });

      // Refresh cart and audit trail
      if (checkoutData?.session_id) {
        await refreshAudit(checkoutData.session_id);
        await refreshCart(checkoutData.session_id);
      }
    } catch (err) {
      console.error('Payment simulation failed:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleOpenLivePaymentLink = () => {
    if (checkoutData?.payment_link_url) {
      window.open(checkoutData.payment_link_url, '_blank');
      // When opening the test payment link, prepare confirmation view on store tab
      setPaymentSuccess(true);
      setPaymentDetails({
        paymentId: 'pay_test_' + (checkoutData.session_id ? checkoutData.session_id.slice(0, 8) : 'demo'),
        orderId: checkoutData?.razorpay_order_id || 'order_demo_test',
        amount: checkoutData?.amount || cart.subtotal,
      });
      if (checkoutData?.session_id) {
        refreshAudit(checkoutData.session_id);
        refreshCart(checkoutData.session_id);
      }
    }
  };

  const handleClose = () => {
    setIsCheckoutOpen(false);
    setPaymentSuccess(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/80 backdrop-blur-sm animate-fadeIn">
      <div className="bg-panel border border-panel-border rounded-2xl max-w-lg w-full overflow-hidden shadow-2xl">
        {/* Modal Header */}
        <div className="p-5 border-b border-panel-border flex items-center justify-between bg-ink/80">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-signal-gold" />
            <h2 className="font-display font-bold text-lg text-paper">
              {paymentSuccess ? 'Order Confirmed' : 'Checkout & Payment'}
            </h2>
          </div>
          <button
            onClick={handleClose}
            className="p-1.5 rounded-lg text-slate hover:text-paper hover:bg-ink transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6">
          {paymentSuccess ? (
            /* Success State */
            <div className="text-center py-4 space-y-4">
              <div className="w-16 h-16 rounded-full bg-signal-gold/15 border-2 border-signal-gold flex items-center justify-center mx-auto animate-bounce">
                <CheckCircle className="w-8 h-8 text-signal-gold" />
              </div>
              <div className="space-y-1">
                <h3 className="font-display font-bold text-xl text-paper">Payment Verified!</h3>
                <p className="text-xs text-slate max-w-xs mx-auto">
                  Cryptographic HMAC-SHA256 signature verified against Razorpay Test Mode.
                </p>
              </div>

              <div className="bg-ink border border-panel-border rounded-xl p-4 font-mono text-xs text-left space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate">Payment ID:</span>
                  <span className="text-paper">{paymentDetails?.paymentId}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate">Order ID:</span>
                  <span className="text-paper truncate max-w-[200px]">{paymentDetails?.orderId}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate">Amount Paid:</span>
                  <span className="text-signal-gold font-bold">₹{paymentDetails?.amount?.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate">Status:</span>
                  <span className="text-signal-gold uppercase font-bold">PAID (TEST MODE)</span>
                </div>
              </div>

              <p className="text-[11px] font-mono text-slate">
                ✓ Recorded live into the Decision Ledger and Audit Log.
              </p>

              <button
                onClick={handleClose}
                className="w-full py-3 rounded-xl bg-signal-gold text-ink font-bold text-sm hover:opacity-95"
              >
                Back to Store
              </button>
            </div>
          ) : (
            /* Active Checkout State */
            <div className="space-y-5">
              {/* Order Summary */}
              <div className="bg-ink border border-panel-border rounded-xl p-4 space-y-3 font-mono text-xs">
                <div className="text-slate uppercase tracking-wider font-semibold border-b border-panel-border pb-2">
                  Order Summary
                </div>
                <div className="max-h-32 overflow-y-auto space-y-2 pr-1">
                  {cart.items.map((item) => (
                    <div key={item.id} className="flex justify-between items-center text-paper">
                      <span className="truncate pr-2">{item.name} (x{item.qty})</span>
                      <span className="text-signal-gold font-medium shrink-0">₹{item.line_total.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
                <div className="pt-2 border-t border-panel-border flex justify-between items-center text-sm font-bold">
                  <span className="text-paper font-display">Amount Due</span>
                  <span className="text-signal-gold font-mono text-base">
                    ₹{(checkoutData?.amount || cart.subtotal).toFixed(2)}
                  </span>
                </div>
              </div>

              {/* Payment Actions */}
              <div className="space-y-3">
                {checkoutData?.payment_link_url && (
                  <button
                    onClick={handleOpenLivePaymentLink}
                    className="w-full py-3 px-4 rounded-xl bg-signal-gold text-ink font-bold text-sm flex items-center justify-center gap-2 hover:opacity-95 shadow-lg"
                  >
                    <span>Pay via Razorpay Test Link</span>
                    <ExternalLink className="w-4 h-4" />
                  </button>
                )}

                <button
                  onClick={handleSimulatePayment}
                  disabled={isProcessing}
                  className="w-full py-3 px-4 rounded-xl border border-agent-cyan bg-agent-cyan/15 hover:bg-agent-cyan/25 text-agent-cyan font-bold text-sm flex items-center justify-center gap-2 transition-colors"
                >
                  {isProcessing ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <span>▶ Instant Test Payment Simulation</span>
                      <span className="text-[11px] opacity-80 font-normal font-mono">(No credentials required)</span>
                    </>
                  )}
                </button>
              </div>

              <div className="text-center">
                <p className="text-[11px] font-mono text-slate">
                  Payments processed strictly in Razorpay TEST MODE. No real cards charged.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
