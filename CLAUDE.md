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
- Do not implement CT-e1 GUI automation inside this repository. See CT-e1 GUI automation exception below.
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
- 3回運用する場合、各時刻前にCSVが inbox に存在する必要がある。2026-06-28以降、手動配置だけでなく external RPA が上流候補。詳細は CT-e1 RPA / Call Loss pipeline bridge 参照。
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

### CT-e1 GUI automation exception

The general rule remains: do not implement CT-e1 login automation inside this repository.

CT-e1 GUI automation is allowed only in the external local workspace below, and must not be ported into this repository:

C:\Users\User\Documents\Projects\multi-multi-os-local\ct_e1_export_rpa

The main multi-multi-os repository consumes CT-e1 CSV files from data/ct_e1/inbox; it does not own the CT-e1 screen RPA implementation.



<!-- CT_E1_RPA_PIPELINE_BRIDGE_START -->
## CT-e1 RPA / Call Loss pipeline bridge

As of 2026-06-29, CT-e1 has two separate mechanisms that must be understood as one pipeline:

- Upstream: external CT-e1 RPA in C:\Users\User\Documents\Projects\multi-multi-os-local\ct_e1_export_rpa
- Downstream: existing multi-multi-os Call Loss processing that consumes CSV files from data/ct_e1/inbox

Pipeline:

CT-e1 report condition screen visible/frontmost -> external RPA outputs CSV to inbox -> Call Loss task imports/processes that CSV.

The old 2026-06-25 status that says CSV must exist in inbox before each Call Loss run remains true as a downstream requirement, but it should no longer be read as manual placement only. From 2026-06-28 onward, the CSV may be placed by the external RPA.

Interim operation on the current PC:

- Human prepares CT-e1 login/navigation/report condition screen.
- Human runs the RPA BAT manually.
- Scheduler is not the main value on the current PC because the condition screen is not guaranteed to be ready at trigger time.

Target operation on the separate PC:

- Keep CT-e1 logged in with the report condition screen visible/frontmost.
- Schedule external RPA at the cutoff time.
- Schedule Call Loss after the RPA has enough time to finish.

Recommended schedule design:

- 18:00 RPA acquisition -> 18:10 Call Loss
- 20:00 RPA acquisition -> 20:10 Call Loss
- 21:00 RPA acquisition -> 21:10 Call Loss
- Optional hourly extension after 18:00: 19:00 RPA acquisition -> 19:10 Call Loss

Do not describe this as CT-e1 login-to-CSV fully unattended automation. Accurate scope remains: report condition screen visible/frontmost -> output -> save -> inbox.
<!-- CT_E1_RPA_PIPELINE_BRIDGE_END -->

<!-- CT_E1_EXTERNAL_RPA_STATUS_START -->
## CT-e1 external CSV acquisition RPA status

As of 2026-06-28, CT-e1 通話呼詳細V3.5(CSV) acquisition has an external local RPA implementation outside this repository.

Scope boundary:

- multi-multi-os remains responsible for consuming CSV files from data/ct_e1/inbox.
- CT-e1 screen automation is managed only in C:\Users\User\Documents\Projects\multi-multi-os-local\ct_e1_export_rpa.
- Do not move CT-e1 GUI automation code into this repository.
- CT-e1 login/navigation before the report condition screen is not treated as completed unattended automation.

Confirmed result:

- FULL_AUTO_SUCCESS was achieved for the segment: CT-e1 report condition screen visible/frontmost -> V9 output button auto-click -> V8 save dialog handling -> inbox CSV saved.
- Success CSV: C:\Users\User\Documents\Projects\multi-multi-os\data\ct_e1\inbox\通話呼詳細V3.5(CSV)_20260627192106.csv
- Success log: C:\Users\User\Documents\Projects\multi-multi-os-local\ct_e1_export_rpa\logs\FULL_CHAIN_ONE_LIVE_NO_HUMAN_CLICK_20260627_192033.log

Current adoption pointer:

- Operation candidate: C:\Users\User\Documents\Projects\multi-multi-os-local\ct_e1_export_rpa\_KNOWN_GOOD_FULL_AUTO_PLUS_RED_GUARD_STATIC_OK_20260628_213233
- Proven live baseline: C:\Users\User\Documents\Projects\multi-multi-os-local\ct_e1_export_rpa\_KNOWN_GOOD_FULL_AUTO_CTE1_CSV_TO_INBOX_20260628_172313
- Note: the red pixel guard fix is statically verified but has not had a post-fix Live run.

Operational wording:

Do not describe this as full CT-e1 login-to-CSV unattended automation. The accurate description is: report condition screen visible/frontmost からの 出力 -> 保存 -> inbox保存 の無人化.
<!-- CT_E1_EXTERNAL_RPA_STATUS_END -->
