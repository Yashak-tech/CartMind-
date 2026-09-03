import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import * as api from '../api';

const CartContext = createContext(null);

export function CartProvider({ children }) {
  const [sessionId, setSessionId] = useState(() => localStorage.getItem('cartmind_session_id') || '');
  const [products, setProducts] = useState([]);
  const [cart, setCart] = useState({ items: [], subtotal: 0, total_items: 0, status: 'active' });
  const [auditFeed, setAuditFeed] = useState([]);
  const [chatMessages, setChatMessages] = useState([
    {
      id: 'welcome_1',
      role: 'agent',
      text: "Welcome to CartMind! I'm your AI shopping assistant. Browse our curated gear, ask me for pairing recommendations, or request a discount code. Every decision I make is verified and audited live in the Decision Ledger below.",
      decisions: [],
      timestamp: new Date().toISOString(),
    },
  ]);
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [isCheckoutOpen, setIsCheckoutOpen] = useState(false);
  const [checkoutData, setCheckoutData] = useState(null);
  const [isThinking, setIsThinking] = useState(false);
  const [isLoadingProducts, setIsLoadingProducts] = useState(true);
  const [errorMessage, setErrorMessage] = useState(null);

  // Initialize or restore session
  const initSession = useCallback(async () => {
    try {
      let activeId = sessionId;
      if (!activeId) {
        const sessionRes = await api.createSession();
        activeId = sessionRes.session_id;
        setSessionId(activeId);
        localStorage.setItem('cartmind_session_id', activeId);
      }
      return activeId;
    } catch (err) {
      console.error('Failed to initialize session:', err);
      return null;
    }
  }, [sessionId]);

  // Load products catalog
  const loadProducts = useCallback(async () => {
    try {
      setIsLoadingProducts(true);
      const data = await api.fetchProducts();
      setProducts(data);
    } catch (err) {
      console.error('Failed to load products:', err);
    } finally {
      setIsLoadingProducts(false);
    }
  }, []);

  // Refresh cart state
  const refreshCart = useCallback(async (sid) => {
    const id = sid || sessionId;
    if (!id) return;
    try {
      const data = await api.getCart(id);
      // Auto-rollover if the stored session was already checked out
      if (data.status === 'checked_out') {
        const newSession = await api.createSession();
        setSessionId(newSession.session_id);
        localStorage.setItem('cartmind_session_id', newSession.session_id);
        setCart({ items: [], subtotal: 0, total_items: 0, status: 'active' });
        return;
      }
      setCart(data);
    } catch (err) {
      console.error('Failed to refresh cart:', err);
    }
  }, [sessionId]);

  // Refresh audit trail
  const refreshAudit = useCallback(async (sid) => {
    const id = sid || sessionId;
    if (!id) return;
    try {
      const data = await api.fetchAuditTrail(id);
      if (data && data.timeline) {
        setAuditFeed(data.timeline);
      }
    } catch (err) {
      console.error('Failed to refresh audit:', err);
    }
  }, [sessionId]);

  // Initial bootstrap
  useEffect(() => {
    async function bootstrap() {
      await loadProducts();
      const sid = await initSession();
      if (sid) {
        await refreshCart(sid);
        await refreshAudit(sid);
      }
    }
    bootstrap();
  }, [initSession, loadProducts, refreshCart, refreshAudit]);

  // Add product to cart
  const addToCart = async (productId, qty = 1) => {
    try {
      setErrorMessage(null);
      let sid = sessionId;
      if (!sid || cart.status === 'checked_out') {
        const newSession = await api.createSession();
        sid = newSession.session_id;
        setSessionId(sid);
        localStorage.setItem('cartmind_session_id', sid);
      }
      const updatedCart = await api.addToCart(sid, productId, qty);
      setCart(updatedCart);
      await refreshAudit(sid);
      return { success: true };
    } catch (err) {
      if (err.message && err.message.includes('checked_out')) {
        const newSession = await api.createSession();
        setSessionId(newSession.session_id);
        localStorage.setItem('cartmind_session_id', newSession.session_id);
        const retryCart = await api.addToCart(newSession.session_id, productId, qty);
        setCart(retryCart);
        await refreshAudit(newSession.session_id);
        return { success: true };
      }
      setErrorMessage(err.message);
      return { success: false, error: err.message };
    }
  };

  // Remove item from cart
  const removeFromCart = async (itemId) => {
    try {
      const sid = sessionId || await initSession();
      const updatedCart = await api.removeFromCart(sid, itemId);
      setCart(updatedCart);
      await refreshAudit(sid);
    } catch (err) {
      console.error('Failed to remove item:', err);
    }
  };

  // Send message to reasoning layer
  const sendMessage = async (text) => {
    if (!text.trim() || isThinking) return;

    let sid = sessionId;
    if (!sid || cart.status === 'checked_out') {
      const newSession = await api.createSession();
      sid = newSession.session_id;
      setSessionId(sid);
      localStorage.setItem('cartmind_session_id', sid);
      setCart({ items: [], subtotal: 0, total_items: 0, status: 'active' });
    }

    const userMsg = {
      id: `usr_${Date.now()}`,
      role: 'user',
      text: text.trim(),
      timestamp: new Date().toISOString(),
    };
    setChatMessages((prev) => [...prev, userMsg]);
    setIsThinking(true);

    try {
      const response = await api.sendChatMessage(sid, text);

      const agentMsg = {
        id: `agt_${Date.now()}`,
        role: 'agent',
        text: response.reply,
        decisions: response.decisions || [],
        timestamp: new Date().toISOString(),
      };
      setChatMessages((prev) => [...prev, agentMsg]);

      // If cart changed
      if (response.cart) {
        setCart(response.cart);
      }

      // Check if initiate_checkout was approved
      const checkoutDecision = (response.decisions || []).find(
        (d) => d.tool_name === 'initiate_checkout' && d.decision === 'approved'
      );
      if (checkoutDecision) {
        startCheckout();
      }

      await refreshAudit(sid);
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        {
          id: `err_${Date.now()}`,
          role: 'agent',
          text: `I encountered an issue processing that: ${err.message}`,
          decisions: [],
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsThinking(false);
    }
  };

  // Start checkout flow
  const startCheckout = async () => {
    try {
      const sid = sessionId || await initSession();
      const order = await api.initiateCheckout(sid);
      setCheckoutData(order);
      setIsCheckoutOpen(true);
      await refreshAudit(sid);
      return order;
    } catch (err) {
      setErrorMessage(err.message);
      return null;
    }
  };

  // Reset to a new session
  const resetSession = async () => {
    localStorage.removeItem('cartmind_session_id');
    setSessionId('');
    const newSession = await api.createSession();
    setSessionId(newSession.session_id);
    localStorage.setItem('cartmind_session_id', newSession.session_id);
    setCart({ items: [], subtotal: 0, total_items: 0, status: 'active' });
    setAuditFeed([]);
    setChatMessages([
      {
        id: 'welcome_new',
        role: 'agent',
        text: "Started a fresh shopping session. What are you looking to gear up with today?",
        decisions: [],
        timestamp: new Date().toISOString(),
      },
    ]);
  };

  return (
    <CartContext.Provider
      value={{
        sessionId,
        products,
        cart,
        auditFeed,
        chatMessages,
        isCartOpen,
        setIsCartOpen,
        isCheckoutOpen,
        setIsCheckoutOpen,
        checkoutData,
        isThinking,
        isLoadingProducts,
        errorMessage,
        setErrorMessage,
        addToCart,
        removeFromCart,
        sendMessage,
        startCheckout,
        refreshCart,
        refreshAudit,
        resetSession,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const context = useContext(CartContext);
  if (!context) throw new Error('useCart must be used within CartProvider');
  return context;
}
