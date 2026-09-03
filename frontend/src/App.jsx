import React, { useState } from 'react';
import { CartProvider } from './context/CartContext';
import Header from './components/Header';
import Storefront from './components/Storefront';
import AgentRail from './components/AgentRail';
import CartDrawer from './components/CartDrawer';
import CheckoutModal from './components/CheckoutModal';
import AuditView from './pages/AuditView';
import { Bot, ShoppingBag } from 'lucide-react';

export default function App() {
  const [currentView, setCurrentView] = useState('shop'); // 'shop' | 'audit'
  const [mobileTab, setMobileTab] = useState('store'); // 'store' | 'agent' for mobile

  return (
    <CartProvider>
      <div className="h-screen w-screen flex flex-col bg-ink text-paper overflow-hidden">
        {/* Persistent Top Navigation */}
        <Header currentView={currentView} setCurrentView={setCurrentView} />

        {/* Mobile View Toggle Bar */}
        {currentView === 'shop' && (
          <div className="lg:hidden flex border-b border-panel-border bg-panel text-xs font-mono">
            <button
              onClick={() => setMobileTab('store')}
              className={`flex-1 py-2.5 flex items-center justify-center gap-2 font-semibold ${
                mobileTab === 'store'
                  ? 'bg-ink text-signal-gold border-b-2 border-signal-gold'
                  : 'text-slate'
              }`}
            >
              <ShoppingBag className="w-4 h-4" />
              Storefront
            </button>
            <button
              onClick={() => setMobileTab('agent')}
              className={`flex-1 py-2.5 flex items-center justify-center gap-2 font-semibold ${
                mobileTab === 'agent'
                  ? 'bg-ink text-agent-cyan border-b-2 border-agent-cyan'
                  : 'text-slate'
              }`}
            >
              <Bot className="w-4 h-4 text-agent-cyan" />
              Agent Rail & Ledger
            </button>
          </div>
        )}

        {/* Main Content Area */}
        <div className="flex-1 flex min-h-0 overflow-hidden">
          {currentView === 'audit' ? (
            /* Full-width dedicated /audit View */
            <AuditView />
          ) : (
            /* Split-Screen Commerce Workspace (FRONTEND_PROMPT.md §3) */
            <div className="flex-1 flex flex-col lg:flex-row min-h-0 w-full overflow-hidden">
              {/* Left: Storefront (takes all available width, scrolls smoothly) */}
              <div
                className={`flex-1 min-w-0 flex flex-col h-full overflow-hidden ${
                  mobileTab === 'store' ? 'flex' : 'hidden lg:flex'
                }`}
              >
                <Storefront />
              </div>

              {/* Right: Fixed Agent Rail (spacious 480-580px column, full vertical height for AI Chatbot) */}
              <div
                className={`w-full lg:w-[480px] xl:w-[540px] 2xl:w-[580px] shrink-0 h-full flex flex-col border-l border-panel-border bg-ink ${
                  mobileTab === 'agent' ? 'flex' : 'hidden lg:flex'
                }`}
              >
                <AgentRail />
              </div>
            </div>
          )}
        </div>

        {/* Overlays */}
        <CartDrawer />
        <CheckoutModal />
      </div>
    </CartProvider>
  );
}
