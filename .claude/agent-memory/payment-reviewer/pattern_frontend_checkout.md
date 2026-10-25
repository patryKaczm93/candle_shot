---
name: frontend-checkout-patterns
description: Recurring weak spots in the checkout form (story 5.2) - double submit, bfcache back from Stripe, unvalidated redirect url
metadata:
  type: feedback
---

- Double-submit guard via `useState` busy only (stale closure); backend has no per-request idempotency (Stripe key is per order number), so each extra POST = new order + stock reservation held ~30 min. Prefer a `useRef` lock.
- After `window.location.assign` busy stays true; returning with Back (bfcache) can leave the form stuck, while the old pending order still holds stock.
- Redirect url from the API is not checked (`https://checkout.stripe.com/`); a malformed response would navigate to a relative URL.
- Frontend shipping price fallback `?? 0` shows "Gratis" when the method is missing from /api/shipping (informational only).
- Frontend/backend validation parity (phone, NIP, locker, postal code, discriminated `shipping` loc) verified OK in 5.2; re-check when schemas.py changes.

**Why:** found in the 5.2 review.
**How to apply:** check first when the form, api.ts or CheckoutIn change.
