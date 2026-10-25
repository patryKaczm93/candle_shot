---
name: checkout-review-patterns
description: Recurring weak spots found in payment-path reviews (story 5.1 onward) in the candle shop
metadata:
  type: feedback
---

- Side effects at Stripe before DB commit: every failure after `sessions.create` (amount_total mismatch, commit error) leaves a live orphan session unless `sessions.expire` is called best-effort.
- Unauthenticated checkout reserves stock with no rate limit: stock-hoarding DoS (pending holds stock up to 31 min, released only by the 6.2 expired webhook). Re-check when 6.x lands.
- Stripe client without explicit timeout: default ~80 s while holding FOR UPDATE locks and a DB connection.
- ORM `FOR UPDATE` does not refresh already-loaded attributes without `populate_existing()`; `stock -= qty` writes an absolute value, not `stock = stock - qty`. Safe only under the lock with a fresh session.
- Fakes that compute `amount_total` from the sent line_items make the amount_total check tautological; the mismatch branch needs its own test.
- Test fixture `db` uses rollback, so rollback tests need a prior commit (`keep(db)`), otherwise they pass falsely.

**Why:** found in the 5.1 review; likely to repeat in webhook (6.x) work.
**How to apply:** check these first in later reviews.
