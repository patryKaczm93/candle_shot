---
name: post-commit-side-effects-never-raise
description: Recurring pattern in webhook side effects (e-mail) - "never raises" claims leak exceptions outside the try block
metadata:
  type: feedback
---

In `app/services/emails.py` (story 6.3) docstrings claim "Never raises", but message-building ran outside the try/except. Any post-commit callback in `handle_event` should also be wrapped by the caller (500 after commit = Stripe retry returns 200 as duplicate, side effect lost).

**Why:** the event is already recorded, so the side effect is never redone.
**How to apply:** check the call site in `webhooks.handle_event` catches Exception; check alert mails about money problems have a log fallback with order number and payment intent (no PII); check tests block the network globally (patch urlopen), not only via an empty API key.
