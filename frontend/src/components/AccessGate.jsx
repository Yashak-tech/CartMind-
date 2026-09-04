import React, { useState, useEffect } from 'react';
import * as api from '../api';
import { Shield, KeyRound, Mail, ArrowRight, CheckCircle2, AlertTriangle, RefreshCw, Lock, Sparkles } from 'lucide-react';

export default function AccessGate({ onAuthenticated }) {
  const [step, setStep] = useState('email'); // 'email' | 'code'
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [devCode, setDevCode] = useState('');
  const [resendCooldown, setResendCooldown] = useState(0);

  // Resend cooldown timer
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => {
      setResendCooldown((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  const handleRequestCode = async (e) => {
    if (e) e.preventDefault();
    if (!email || !email.includes('@')) {
      setErrorMsg('Please enter a valid email address.');
      return;
    }

    setIsLoading(true);
    setErrorMsg('');
    setSuccessMsg('');

    try {
      const res = await api.requestAccessCode(email);
      setStep('code');
      setResendCooldown(60);
      setSuccessMsg(`Single-use access code sent to ${email}`);
      if (res.dev_code) {
        setDevCode(res.dev_code);
      }
    } catch (err) {
      setErrorMsg(err.message || 'Failed to request access code.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyCode = async (e) => {
    if (e) e.preventDefault();
    if (!code || code.trim().length !== 6) {
      setErrorMsg('Please enter the 6-digit access code.');
      return;
    }

    setIsLoading(true);
    setErrorMsg('');

    try {
      const data = await api.verifyAccessCode(email, code.trim());
      if (onAuthenticated) {
        onAuthenticated(data.token, data.email);
      }
    } catch (err) {
      setErrorMsg(err.message || 'Invalid or expired access code.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#07090E] p-4 font-sans text-paper overflow-y-auto">
      {/* Subtle Background Glows */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-signal-gold/[0.04] rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-agent-cyan/[0.04] rounded-full blur-3xl pointer-events-none" />

      <div className="relative w-full max-w-md bg-panel border border-panel-border rounded-2xl p-6 sm:p-8 shadow-2xl space-y-6">
        {/* Top Restricted Badge */}
        <div className="flex items-center justify-between border-b border-panel-border/70 pb-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-ink border border-panel-border flex items-center justify-center">
              <Shield className="w-4 h-4 text-signal-gold" />
            </div>
            <div>
              <span className="font-display font-extrabold text-sm tracking-wider uppercase text-paper block">
                CARTMIND
              </span>
              <span className="text-[10px] font-mono text-slate uppercase tracking-widest block">
                Access-Gated Preview
              </span>
            </div>
          </div>
          <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold bg-signal-gold/10 border border-signal-gold/30 text-signal-gold uppercase tracking-wider">
            Test Mode
          </span>
        </div>

        {/* Step 1: Request Code Screen */}
        {step === 'email' && (
          <form onSubmit={handleRequestCode} className="space-y-4">
            <div className="space-y-1.5">
              <h2 className="font-display font-black text-xl text-paper tracking-tight">
                Enter Evaluator Email
              </h2>
              <p className="text-xs text-slate leading-relaxed">
                CartMind operates in restricted demo mode for the Razorpay Buildathon. Enter your email to receive a single-use 6-digit access code.
              </p>
            </div>

            {errorMsg && (
              <div className="p-3 rounded-xl bg-alert-coral/10 border border-alert-coral/30 text-alert-coral text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            <div className="space-y-2">
              <label className="text-[11px] font-mono text-slate uppercase tracking-wider block">
                Email Address
              </label>
              <div className="relative flex items-center">
                <Mail className="absolute left-3.5 w-4 h-4 text-slate pointer-events-none" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="evaluator@buildathon.dev"
                  autoFocus
                  required
                  disabled={isLoading}
                  className="w-full pl-10 pr-4 py-3 rounded-xl bg-ink border border-panel-border focus:border-signal-gold text-paper placeholder:text-slate text-sm font-mono focus:outline-none transition-colors"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading || !email}
              className="w-full py-3 px-4 rounded-xl bg-signal-gold text-ink font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 hover:opacity-95 active:scale-98 transition-all disabled:opacity-40 shadow-lg shadow-signal-gold/10"
            >
              {isLoading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Dispatching Access Code...</span>
                </>
              ) : (
                <>
                  <span>Request Access Code</span>
                  <ArrowRight className="w-4 h-4 stroke-[2.5]" />
                </>
              )}
            </button>
          </form>
        )}

        {/* Step 2: Enter 6-Digit Code Screen */}
        {step === 'code' && (
          <form onSubmit={handleVerifyCode} className="space-y-4">
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <h2 className="font-display font-black text-xl text-paper tracking-tight">
                  Verify Access Code
                </h2>
                <button
                  type="button"
                  onClick={() => {
                    setStep('email');
                    setCode('');
                    setErrorMsg('');
                  }}
                  className="text-[11px] font-mono text-signal-gold hover:underline"
                >
                  Change Email
                </button>
              </div>
              <p className="text-xs text-slate leading-relaxed">
                Enter the 6-digit code sent to <strong className="text-paper">{email}</strong>.
              </p>
            </div>

            {successMsg && (
              <div className="p-3 rounded-xl bg-emerald-400/10 border border-emerald-400/30 text-emerald-400 text-xs flex items-center gap-2 font-mono">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span className="truncate">{successMsg}</span>
              </div>
            )}

            {/* Development OTP Quick Fill Preview */}
            {devCode && (
              <div className="p-3 rounded-xl bg-signal-gold/10 border border-signal-gold/30 text-xs space-y-2 font-mono">
                <div className="flex items-center justify-between text-signal-gold font-bold text-[11px]">
                  <span className="flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5" />
                    DEVELOPMENT PREVIEW CODE
                  </span>
                  <button
                    type="button"
                    onClick={() => setCode(devCode)}
                    className="px-2 py-0.5 rounded bg-signal-gold text-ink text-[10px] font-black uppercase hover:opacity-90 active:scale-95"
                  >
                    Auto Fill
                  </button>
                </div>
                <div className="flex items-center justify-between text-slate text-[11px]">
                  <span>Console OTP:</span>
                  <span className="text-paper font-black tracking-widest text-sm">{devCode}</span>
                </div>
              </div>
            )}

            {errorMsg && (
              <div className="p-3 rounded-xl bg-alert-coral/10 border border-alert-coral/30 text-alert-coral text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            <div className="space-y-2">
              <label className="text-[11px] font-mono text-slate uppercase tracking-wider block">
                6-Digit Security Code
              </label>
              <div className="relative flex items-center">
                <KeyRound className="absolute left-3.5 w-4 h-4 text-slate pointer-events-none" />
                <input
                  type="text"
                  maxLength={6}
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                  placeholder="123456"
                  autoFocus
                  required
                  disabled={isLoading}
                  className="w-full pl-10 pr-4 py-3 rounded-xl bg-ink border border-panel-border focus:border-signal-gold text-paper placeholder:text-slate text-center text-lg font-mono font-bold tracking-[0.5em] focus:outline-none transition-colors"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading || code.length !== 6}
              className="w-full py-3 px-4 rounded-xl bg-signal-gold text-ink font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 hover:opacity-95 active:scale-98 transition-all disabled:opacity-40 shadow-lg shadow-signal-gold/10"
            >
              {isLoading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Validating Code...</span>
                </>
              ) : (
                <>
                  <span>Verify & Enter Workspace</span>
                  <ArrowRight className="w-4 h-4 stroke-[2.5]" />
                </>
              )}
            </button>

            {/* Resend Code Action */}
            <div className="pt-1 text-center">
              {resendCooldown > 0 ? (
                <span className="text-[11px] font-mono text-slate">
                  Resend code in {resendCooldown}s
                </span>
              ) : (
                <button
                  type="button"
                  onClick={handleRequestCode}
                  disabled={isLoading}
                  className="text-[11px] font-mono text-slate hover:text-signal-gold underline transition-colors"
                >
                  Didn't receive code? Resend
                </button>
              )}
            </div>
          </form>
        )}

        {/* Security Trust Indicators */}
        <div className="pt-4 border-t border-panel-border/70 grid grid-cols-3 gap-2 text-center text-[10px] font-mono text-slate">
          <div className="p-2 rounded-lg bg-ink border border-panel-border/50">
            <span className="text-signal-gold block font-bold">10% Margin</span>
            <span>Hard Floor</span>
          </div>
          <div className="p-2 rounded-lg bg-ink border border-panel-border/50">
            <span className="text-agent-cyan block font-bold">Pure Python</span>
            <span>Gating Engine</span>
          </div>
          <div className="p-2 rounded-lg bg-ink border border-panel-border/50">
            <span className="text-paper block font-bold">HMAC-SHA256</span>
            <span>Verified Links</span>
          </div>
        </div>
      </div>
    </div>
  );
}
