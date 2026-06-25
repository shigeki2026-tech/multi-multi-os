# CLAUDE.md

## Project

- Repository: multi-multi-os
- App: Streamlit-based local operations dashboard
- Branch: main
- Target path on Shigeki PC: C:\Users\User\Documents\Projects\multi-multi-os

## Non-negotiable rules

- Do not commit SQLite database files.
- Do not commit files under data/ct_e1/.
- Do not commit files under backup/.
- Do not use git add .
- Do not rewrite unrelated UI files.
- Do not modify DB schema unless explicitly requested.
- Do not implement CT-e1 login automation.
- Do not implement CT-e1 GUI automation.
- Do not use private CT-e1 APIs, cookies, tokens, or browser session extraction.
- Do not implement Teams sending unless explicitly requested.
- Do not register Windows Task Scheduler tasks unless explicitly requested.
- Do not apply regex or ad-hoc partial patches when exact file edits are safer.

## Standard local workflow

```powershell
cd "$env:USERPROFILE\Documents\Projects\multi-multi-os"
taskkill /F /IM python.exe 2>$null
git pull origin main
git status --short
```

## Validation commands

```powershell
cd "$env:USERPROFILE\Documents\Projects\multi-multi-os"
python -m compileall app.py src pages scripts
pytest
git status --short
```

## Repository hygiene

- multimulti_os.db was intentionally removed from git tracking.
- backup/ was intentionally removed from git tracking.
- Local DB and local backups may exist on disk, but must not be re-added.
- .gitignore already excludes *.db, *.sqlite, *.sqlite3, data/ct_e1/, backup/, and _local_backups/.

## UI button styling

- Current button color handling is a workaround, not a permanent design.
- src/ui/session.py contains render_button_marker().
- pages/02_タスク.py uses render_button_marker() for task-specific success/danger/secondary buttons.
- Do not expand marker-based CSS unless specifically requested.

## CT-e1 status

- pages/10_CT-e1自動化.py currently supports Phase 0, manual CSV call-loss check, settings, and run log.
- src/services/ct_e1_service.py contains deterministic CSV read, validation, call-loss aggregation, notification text, and CtE1Store.
- Call-loss definition: count only 放棄呼=1; exclude 発信呼=1 first when 発信呼 exists.
- pages/07_呼詳細作成.py is still a placeholder and must not be modified unless requested.

## How to report back

- Summarize changed files.
- Summarize tests run and results.
- Mention any skipped work explicitly.
- Before commit, show git status --short and exact files to be added.
- Use explicit git add paths only.

<!-- CT_E1_CALL_LOSS_CURRENT_STATUS_START -->

## CT-e1 呼損チェック 現在ステータス

更新日: 2026-06-25

### 確定済み

- CT-e1 呼損チェックは、通話呼詳細CSVを対象に実装済み。
- Task Schedulerへの登録済み。
- 登録タスク:
  - CT-e1 Yoshikei Call Loss 18-05
  - CT-e1 Yoshikei Call Loss 20-05
  - CT-e1 Yoshikei Call Loss 21-05
- 実行時刻:
  - 毎日 18:05
  - 毎日 20:05
  - 毎日 21:05
- Task Schedulerの実時刻発火は確認済み。
- 2026-06-25 13:44、画面ロック中のTask Scheduler実行を確認済み。
  - 一時タスク: CT-e1 Yoshikei Call Loss TEMP LOCK
  - LastTaskResult: 0
  - run_log: status=no_csv at 2026-06-25T13:44:01
- Start-ScheduledTask による手動起動は成功確認済み。
- 2026-06-22 20時分のCSV処理成功確認済み。
  - 入力CSV: 通話呼詳細V3.5(CSV)_20260622190439.csv
  - 出力: ct_e1_call_loss_20260622_200957.txt/json
  - 放棄呼: 90
  - alert_count: 4
- 2026-06-25 commit 51a2075 Treat missing CT-e1 CSV as no-op で、CSVなし時の扱いを修正済み。
  - CSVなし:
un_log.jsonl に status=no_csv を記録して exit 0
  - CSVあり: 従来どおり処理
  - CSVあり処理失敗: 異常扱い

### 重要な運用前提

- 現在のTask Scheduler設定は InteractiveToken。
- ログオン中のユーザーセッション前提。
- ログオフ中の完全無人実行は未検証。
- 3回運用する場合、各時刻前にCSVを inbox へ置く必要がある。
  - 18:05前に18時確認用CSV
  - 20:05前に20時確認用CSV
  - 21:05前に21時確認用CSV
- --move-processed 有効のため、1つのCSVを3回使い回す設計ではない。

### 未完了

- ログオフ中実行の検証
- CSV配置SOPの確定
- 失敗通知または日次確認SOP
- Task Scheduler XMLのGit管理要否判断
- リアルタイム放棄呼 .xls 対応要否判断

### 禁止・保留

- CT-e1ログイン自動化へ進まない。
- GUI自動化へ進まない。
- 非公開API / Cookie / token に触らない。
- 複数PCで同じ inbox を叩かない。

<!-- CT_E1_CALL_LOSS_CURRENT_STATUS_END -->

<!-- CT_E1_CSV_SOP_REFERENCE_START -->

## CT-e1 CSV配置SOP

CSV配置・処理判定・一時タスク検証の詳細は以下を参照。

    docs/ct_e1_csv_placement_sop.md

<!-- CT_E1_CSV_SOP_REFERENCE_END -->
