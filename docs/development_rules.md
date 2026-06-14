# Development Rules

## 原則

このリポジトリは repo-first で運用する。

## 禁止事項

- 起動中の Streamlit / python.exe に対する直接編集は禁止
- live patch 禁止
- regex / 部分一致による ad-hoc パッチ禁止
- SQLite DB 実体を git 管理しない
- UI色問題だけを先に磨かない
- ページ単位の場当たりCSS追加を避ける

## 作業前標準手順

```powershell
cd "$env:USERPROFILE\Documents\Projects\multi-multi-os"
taskkill /F /IM python.exe 2>$null
git pull origin main

```

## UI修正方針

- UI不具合はまず `src/ui/session.py` など共通レイヤーを確認する
- marker + 隣接セレクタ依存は workaround として扱う
- 恒久対応では helper 関数化し、ページごとの生書きを減らす

## DB運用方針

- `multimulti_os.db` などのSQLite実体はgit管理しない
- ローカルDBは各PCで保持する
- 初回セットアップ手順またはseed方式を別途整備する
