# CT-e1 Call Loss local wrapper fix

## Result

Run-CtE1YoshikeiCallLoss.ps1 was changed from UNC shared-folder mode to local data/ct_e1 mode.

## Reason

External CT-e1 RPA saves CSV to local data/ct_e1/inbox on the current PC.
The old wrapper checked the shared UNC inbox and exited 0 as no_csv, so Task Scheduler appeared successful while local CSV was not processed.

## New local paths

- inbox: data/ct_e1/inbox
- outbox: data/ct_e1/outbox
- processed: data/ct_e1/processed
- run_log: data/ct_e1/run_log.jsonl

## Confirmed source CSV

data/ct_e1/inbox/通話呼詳細V3.5(CSV)_20260629155717.csv

## Backup

C:\Users\User\Documents\Projects\multi-multi-os-local\ct_e1_export_rpa\main_repo_backups\Run-CtE1YoshikeiCallLoss.ps1.bak_before_local_base_20260629_171616
