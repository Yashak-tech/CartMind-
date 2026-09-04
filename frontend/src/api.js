/**
 * CartMind API Client.
 * Connects the frontend to FastAPI endpoints defined in TRD.md §5.
 * Contains ZERO client-side gating or policy calculations.
 */

export const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');
const TOKEN_KEY = 'cartmind_access_token';
const EMAIL_KEY = 'cartmind_access_email';

export function getAuthToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getAuthEmail() {
  return localStorage.getItem(EMAIL_KEY);
}

export function setAuthSession(token, email) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
    if (email) localStorage.setItem(EMAIL_KEY, email);
  } else {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(EMAIL_KEY);
  }
}

export function clearAuthSession() {
  setAuthSession(null, null);
  window.dispatchEvent(new CustomEvent('cartmind:unauthorized'));
}

function getHeaders(extra = {}) {
  const token = getAuthToken();
  return {
    'Content-Type': 'application/json',
    ...extra,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function handleResponse(res, fallbackMessage) {
  if (res.status === 401) {
    clearAuthSession();
    throw new Error('Access session expired. Please sign in with an access code.');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: fallbackMessage }));
    throw new Error(err.detail || fallbackMessage);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Access Gate Authentication Endpoints
// ---------------------------------------------------------------------------
export async function requestAccessCode(email) {
  const res = await fetch(`${API_BASE}/auth/request-code`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  return handleResponse(res, 'Failed to request access code');
}

export async function verifyAccessCode(email, code) {
  const res = await fetch(`${API_BASE}/auth/verify-code`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, code }),
  });
  const data = await handleResponse(res, 'Failed to verify access code');
  setAuthSession(data.token, data.email);
  return data;
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
