---
name: admin-panel-patterns
description: Recurring pitfalls found reviewing the sqladmin panel (stock/prices) in this shop
metadata:
  type: project
---

- Delta-based stock edit (`stock += new - seen`) is NOT idempotent: double submit, two tabs or browser Back replay the same hidden `stock_seen` and add the change twice. Prefer compare-and-set (`SET stock = new WHERE stock = seen`). See backend/app/admin.py StockAdmin.
- Owner-facing stock wording must mean "still sellable" (DB stock already excludes pending reservations and paid-unshipped orders), not "on the shelf"; otherwise typing the physical count oversells.
- WTForms `Regexp(r"^...$")` accepts a trailing newline; use `\Z`.
- Money/number parsing: ASCII regex `[0-9]` is safe; `str.isdigit()` is not (non-ASCII digits, superscripts that int() rejects).
- Order admin (7.2): "ship" action is a conditional UPDATE in own session (good). Recurring gaps: details route not filtered by status like list/edit; admin dates use server-local tz (`astimezone()`), not Europe/Warsaw; no test with hostile names for XSS in Markup formatters; shipped e-mail failure is only logged (seller sees nothing); refunds in Stripe dashboard are not synced, so a refunded-but-`paid` order can still be shipped (no charge.refunded handler until 9.2).
