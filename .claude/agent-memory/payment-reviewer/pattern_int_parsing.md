---
name: int-parsing-of-money-settings
description: Recurring pitfall in this repo - text-to-int parsing of money settings without upper bound
metadata:
  type: feedback
---

Settings table stores money as text; parsers use `re.fullmatch(r"[0-9]+")` + `int()` (ASCII-only, good) but had no upper bound. `int()` of >4300 digits raises plain ValueError (Python 3.11+), which escapes the custom error handling and gives 500.

**Why:** found in review of story 2.3 (app/services/shipping.py).
**How to apply:** for any parser of money/qty from DB or request, check max length/value bound and that the raised error type is the one the caller catches. Check tests cover whitespace, leading zeros, huge numbers, unicode digits.
