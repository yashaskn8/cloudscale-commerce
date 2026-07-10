import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 20 },  // Ramp-up to 20 users
    { duration: '1m', target: 50 },   // Stable load at 50 users
    { duration: '30s', target: 0 },   // Cool-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests must complete under 500ms
    http_req_failed: ['rate<0.01'],    // Less than 1% failure rate
  },
};

const BASE_URLS = {
  auth: 'http://localhost:8001',
  catalog: 'http://localhost:8002',
  inventory: 'http://localhost:8003',
  order: 'http://localhost:8004',
};

export default function () {
  // ── Scenario 1: Browse Products (Catalog) ───────────────────────────────
  const browseRes = http.get(`${BASE_URLS.catalog}/api/v1/products?page=1&size=10`);
  check(browseRes, {
    'catalog status is 200': (r) => r.status === 200,
    'catalog returns items': (r) => r.json().items !== undefined,
  });
  sleep(1);

  // Extract a product ID if present, otherwise use default
  let productId = '3d1d122b-a94b-47cd-899a-aeaae0056325';
  const items = browseRes.json().items;
  if (items && items.length > 0) {
    productId = items[0].id;
  }

  // Get specific product details (Cache hit path)
  const detailRes = http.get(`${BASE_URLS.catalog}/api/v1/products/${productId}`);
  check(detailRes, {
    'product detail status is 200': (r) => r.status === 200,
  });
  sleep(2);

  // ── Scenario 2: Login (Auth) ─────────────────────────────────────────────
  const loginPayload = JSON.stringify({
    email: 'smoketest@cloudscale.io',
    password: 'SmokeTest123!',
  });
  const loginParams = {
    headers: { 'Content-Type': 'application/json' },
  };
  const loginRes = http.post(`${BASE_URLS.auth}/api/v1/auth/login`, loginPayload, loginParams);
  check(loginRes, {
    'login status is 200 or 401': (r) => r.status === 200 || r.status === 401,
  });
  sleep(1);

  // ── Scenario 3: Check Stock (Inventory) ──────────────────────────────────
  const stockRes = http.get(`${BASE_URLS.inventory}/api/v1/inventory`);
  check(stockRes, {
    'inventory status is 200': (r) => r.status === 200,
  });
  sleep(2);

  // ── Scenario 4: Place Order (Checkout) ───────────────────────────────────
  let token = 'dummy_token';
  if (loginRes.status === 200 && loginRes.json().access_token) {
    token = loginRes.json().access_token;
  }

  const orderPayload = JSON.stringify({
    items: [
      {
        product_id: productId,
        quantity: 1,
      },
    ],
  });
  const orderParams = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  };
  const orderRes = http.post(`${BASE_URLS.order}/api/v1/orders`, orderPayload, orderParams);
  check(orderRes, {
    'checkout status is 201 or 401': (r) => r.status === 201 || r.status === 401 || r.status === 422,
  });
  sleep(3);
}
