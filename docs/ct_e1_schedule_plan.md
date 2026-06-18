# CT-e1 呼損チェック：手動実行とスケジューリング計画

保存済みの CT-e1 CSV を、画面操作なしで呼損チェックするための CLI ラッパーと、
将来のスケジューリングに向けた計画をまとめる。

## 方針（厳守）

- CT-e1 Suite への自動ログイン・GUI自動化・非公開API・Cookie/token利用はしない。
- Teams 本送信はしない（通知文プレビューを生成・保存・標準出力するだけ）。
- DB スキーマは変更しない（実行ログは既存 `CtE1Store` の JSON Lines 追記のみ）。
- Windows Task Scheduler への登録は、本計画の段階では行わない（手順のみ記載）。
- 生 CSV 本文は出力・保存しない（集計サマリと通知文のみ保存）。
- 集計ロジックは既存の決定論サービス `src/services/ct_e1_service.py` に委譲する（再実装しない）。

## 構成

- 入力: `data/ct_e1/inbox/`（CT-e1 から手動エクスポート済みの CSV を置く）
- 出力: `data/ct_e1/outbox/`
  - `ct_e1_call_loss_YYYYMMDD_HHMMSS.txt` … 通知文プレビュー
  - `ct_e1_call_loss_YYYYMMDD_HHMMSS.json` … 集計サマリ（生CSVは含めない）
- 設定/実行ログ: `data/ct_e1/`（`settings.json` / `run_log.jsonl`、既存 `CtE1Store`）
- いずれも `.gitignore` の `data/ct_e1/` 配下であり、git では追跡しない。

## CLI: `scripts/run_ct_e1_call_loss_check.py`

既存サービス関数（`detect_and_read` / `validate_columns` / `aggregate_call_loss` /
`build_notification_text` / `CtE1Store.append_log`）を呼ぶだけの薄いラッパー。

### 手動実行（リポジトリ直下から）

```powershell
cd "$env:USERPROFILE\Documents\Projects\multi-multi-os"

# inbox の最新 *.csv（mtime）を自動選択して処理
python scripts/run_ct_e1_call_loss_check.py

# 単一CSVを明示指定（inbox選択より優先）
python scripts/run_ct_e1_call_loss_check.py --csv data\ct_e1\inbox\sample.csv
```

### 主なオプション

| オプション | 説明 |
| --- | --- |
| `--csv PATH` | 処理する単一 CSV を明示（inbox の最新選択より優先） |
| `--threshold N` | しきい値の上書き（未指定なら設定値、なければ 0） |
| `--target-skill-group NAME` | 対象スキルグループ（繰り返し指定可。指定時は設定値を上書き） |
| `--no-log` | 実行ログ（`run_log.jsonl`）への追記を行わない |
| `--inbox PATH` | 入力フォルダ（既定 `data/ct_e1/inbox`） |
| `--outbox PATH` | 出力フォルダ（既定 `data/ct_e1/outbox`） |
| `--data-dir PATH` | 設定/実行ログのベース（既定 `data/ct_e1`） |

引数なしでも動作する（inbox の最新 CSV を選ぶ）。

### 終了コード

| コード | 意味 |
| --- | --- |
| 0 | 成功 |
| 1 | CSV が見つからない |
| 2 | CSV 読込 / 必須列 / 業務エラー |
| 3 | 予期しないエラー |

スケジューラやバッチから呼ぶ際は、この終了コードで成否を判定できる。

## 設定の優先順位

`CLI 上書き > settings.json（CtE1Store）> 既定値`

- しきい値: `--threshold` →（なければ）`settings.threshold` →（なければ）`0`
- 対象スキルグループ: `--target-skill-group`（複数可）→（なければ）`settings.target_skill_groups`
  （改行区切り文字列）→（なければ）全グループ対象

`settings.json` は既存のページ `pages/10_CT-e1自動化.py` の「設定」タブと同じファイルを共有する。

## 将来のスケジューリング（未登録・計画のみ）

本段階では Task Scheduler への登録は行わない。登録する場合は、別途明示的な依頼を受けてから
以下の方針で検討する。

1. 実行コマンドは上記 CLI をそのまま使う（例: 18:00 / 20:00 / 21:00 の呼損確認）。
2. 事前に CT-e1 からの CSV エクスポートを `data/ct_e1/inbox/` に置く運用を確定する
   （CSV 取得自体の自動化は本リポジトリの対象外）。
3. 成否は終了コードで監視する。出力 `.txt` / `.json` を確認用に残す。
4. Teams 本送信が必要になった場合は、別タスクとして明示依頼の上で追加する
   （本 CLI は通知文プレビューの生成までに留める）。

## 検証

```powershell
cd "$env:USERPROFILE\Documents\Projects\multi-multi-os"
python -m compileall app.py src pages scripts
pytest
git status --short
```
