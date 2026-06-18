# Claude Task: CT-e1 Scheduling Follow-up

## Goal

Investigate and continue the already-started CT-e1 automation/scheduling work without expanding scope.

## Important context

This project has already done some CT-e1 work before. Do not assume the feature starts from zero.

Known current implementation:

- pages/10_CT-e1自動化.py has Phase 0 confirmation, manual CSV call-loss check, settings, and run log.
- src/services/ct_e1_service.py has deterministic call-loss aggregation logic.
- tests/test_ct_e1_call_loss.py covers core call-loss behavior.
- pages/07_呼詳細作成.py is still marked as 未実装.

## Required investigation first

Before writing code, inspect:

1. pages/10_CT-e1自動化.py
2. src/services/ct_e1_service.py
3. tests/test_ct_e1_call_loss.py
4. docs/development_rules.md
5. docs/setup_local.md
6. git log --oneline -20

Then report:

- what is already implemented
- what is missing
- whether scheduling code already exists anywhere
- safest next implementation unit

## Scope allowed

Allowed only if missing and clearly justified:

- CLI wrapper for processing an already-saved CT-e1 CSV
- tests for that CLI/wrapper
- documentation for manual execution and later scheduling

## Scope forbidden

- Do not automate CT-e1 login.
- Do not automate CT-e1 GUI operations.
- Do not use private APIs, cookies, tokens, or browser session extraction.
- Do not send Teams messages.
- Do not register Windows Task Scheduler yet.
- Do not modify DB schema.
- Do not modify pages/07_呼詳細作成.py unless explicitly asked.
- Do not commit generated CSV, JSON, TXT, DB, or backup files.

## Expected output

Start by producing a short plan only.

Do not edit files until the plan is reviewed.
