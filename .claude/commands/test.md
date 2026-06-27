---
description: Run ruff + pytest and summarize the results.
allowed-tools: Bash
---

Run the quality gate and report a concise summary.

Lint output:
!`. .venv/bin/activate 2>/dev/null; ruff check . 2>&1 | tail -30`

Test output:
!`. .venv/bin/activate 2>/dev/null; pytest 2>&1 | tail -40`

Summarize: pass/fail counts, and for any failure give the test name, the assertion, and the likely cause. If everything is green, say so in one line.
