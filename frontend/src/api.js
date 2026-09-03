/**
 * CartMind API Client.
 * Connects the frontend to FastAPI endpoints defined in TRD.md §5.
 * Contains ZERO client-side gating or policy calculations.
 */

const API_BASE = 'http://127.0.0.1:8000';

export async function createSession() {
  const res = await fetch(`${API_BASE}/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error('Failed to create shopping session');
  return res.json();
}

export async function fetchProducts() {
  const res = await fetch(`${API_BASE}/products`);
  if (!res.ok) throw new Error('Failed to fetch catalog');
  return res.json();
}

export async function getCart(sessionId) {
  const res = await fetch(`${API_BASE}/session/${sessionId}/cart`);
  if (!res.ok) throw new Error('Failed to fetch cart');
  return res.json();
}

export async function addToCart(sessionId, productId, qty = 1) {
  const res = await fetch(`${API_BASE}/session/${sessionId}/cart/items`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ product_id: productId, qty }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to add item' }));
    throw new Error(err.detail || 'Failed to add item');
  }
  return res.json();
}

export async function removeFromCart(sessionId, itemId) {
  const res = await fetch(`${API_BASE}/session/${sessionId}/cart/items/${itemId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to remove item');
  return res.json();
}

export async function sendChatMessage(sessionId, message) {
  const res = await fetch(`${API_BASE}/session/${sessionId}/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Message error' }));
    throw new Error(err.detail || 'Failed to send message');
  }
  return res.json();
}

export async function initiateCheckout(sessionId) {
  const res = await fetch(`${API_BASE}/session/${sessionId}/checkout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Checkout error' }));
    throw new Error(err.detail || 'Failed to initiate checkout');
  }
  return res.json();
}

export async function fetchAuditTrail(sessionId) {
  const res = await fetch(`${API_BASE}/audit/${sessionId}`);
  if (!res.ok) throw new Error('Failed to fetch audit trail');
  return res.json();
}

export async function listAuditSessions() {
  const res = await fetch(`${API_BASE}/audit`);
  if (!res.ok) throw new Error('Failed to list sessions');
  return res.json();
}
