# CT-e1 Call Loss today-only scheduler fix

## Problem

The 18:05 scheduler processed a stale 2026/06/27 CSV left in local inbox.
The output ct_e1_call_loss_20260629_181302 was not a valid 2026/06/29 18:05 result.

## Fix

- Quarantined stale inbox CSV files.
- Invalidated the stale 18:13 outbox result by moving it to outbox_archive.
- Updated Run-CtE1YoshikeiCallLoss.ps1 to process only today's CSV by filename date.
- The wrapper now passes --csv explicitly to avoid Python selecting stale files from inbox.

## Operational rule

For each cutoff, place a fresh same-day CT-e1 CSV into data/ct_e1/inbox before the scheduled Call Loss task.
If no same-day CSV exists, the task exits 0 as no_csv.

## Backup

C:\Users\User\Documents\Projects\multi-multi-os-local\ct_e1_export_rpa\main_repo_backups\Run-CtE1YoshikeiCallLoss.ps1.bak_before_today_only_20260629_184642

## Stale inbox archive

.\data\ct_e1\inbox_archive\stale_before_today_only_filter_20260629_184642

## Invalid outbox archive

.\data\ct_e1\outbox_archive\invalid_stale_input_20260629_184642
