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
