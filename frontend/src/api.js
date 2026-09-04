/**
 * CartMind API Client.
 * Connects the frontend to FastAPI endpoints defined in TRD.md §5.
 * Contains ZERO client-side gating or policy calculations.
 */

export const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');

function getHeaders(extra = {}) {
  return {
    'Content-Type': 'application/json',
    ...extra,
  };
}

async function handleResponse(res, fallbackMessage) {
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: fallbackMessage }));
    throw new Error(err.detail || fallbackMessage);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Storefront & Cart Endpoints
// ---------------------------------------------------------------------------
export async function createSession() {
  const res = await fetch(`${API_BASE}/session`, {
    method: 'POST',
    headers: getHeaders(),
  });
  return handleResponse(res, 'Failed to create shopping session');
}

export async function fetchProducts() {
  const res = await fetch(`${API_BASE}/products`, {
    headers: getHeaders(),
  });
  return handleResponse(res, 'Failed to fetch catalog');
}

export async function getCart(sessionId) {
  const res = await fetch(`${API_BASE}/session/${sessionId}/cart`, {
    headers: getHeaders(),
  });
  return handleResponse(res, 'Failed to fetch cart');
}

export async function addToCart(sessionId, productId, qty = 1) {
  const res = await fetch(`${API_BASE}/session/${sessionId}/cart/items`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ product_id: productId, qty }),
  });
  return handleResponse(res, 'Failed to add item to cart');
}

export async function removeFromCart(sessionId, itemId) {
  const res = await fetch(`${API_BASE}/session/${sessionId}/cart/items/${itemId}`, {
    method: 'DELETE',
    headers: getHeaders(),
  });
  return handleResponse(res, 'Failed to remove item from cart');
}

export async function sendChatMessage(sessionId, message) {
  const res = await fetch(`${API_BASE}/session/${sessionId}/message`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ message }),
  });
  return handleResponse(res, 'Failed to send chat message');
}

export async function initiateCheckout(sessionId) {
  const res = await fetch(`${API_BASE}/session/${sessionId}/checkout`, {
    method: 'POST',
    headers: getHeaders(),
  });
  return handleResponse(res, 'Failed to initiate checkout');
}

export async function fetchAuditTrail(sessionId) {
  const res = await fetch(`${API_BASE}/audit/${sessionId}`, {
    headers: getHeaders(),
  });
  return handleResponse(res, 'Failed to fetch audit trail');
}

export async function listAuditSessions() {
  const res = await fetch(`${API_BASE}/audit`, {
    headers: getHeaders(),
  });
  return handleResponse(res, 'Failed to list audit sessions');
}

export async function getMetricsSummary() {
  const res = await fetch(`${API_BASE}/api/metrics/summary`, {
    headers: getHeaders(),
  });
  return handleResponse(res, 'Failed to fetch metrics summary');
}

export async function depleteStock(productId = 15) {
  const res = await fetch(`${API_BASE}/products/${productId}/deplete-stock`, {
    method: 'POST',
    headers: getHeaders(),
  });
  return handleResponse(res, `Failed to deplete stock for product ${productId}`);
}

export async function simulateTestPayment() {
  const res = await fetch(`${API_BASE}/api/test-payment/simulate`, {
    method: 'POST',
    headers: getHeaders(),
  });
  return handleResponse(res, 'Failed to simulate test payment');
}

export async function callPaymentCallback(callbackUrl) {
  const fullUrl = callbackUrl.startsWith('http') ? callbackUrl : `${API_BASE}${callbackUrl}`;
  const res = await fetch(fullUrl, {
    method: 'GET',
    headers: getHeaders(),
  });
  return handleResponse(res, 'Failed to trigger payment callback');
}
