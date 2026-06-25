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

## 共有フォルダ運用（inbox / outbox / processed）

複数人・複数PCで同じ共有フォルダ（UNC パス）を使う場合のフォルダ構成。
`--inbox` / `--outbox` / `--data-dir` / `--processed-dir` には UNC パスをそのまま指定できる。

```
（共有フォルダのルート）
├─ inbox/       … CT-e1 から手動エクスポートした CSV を置く
├─ outbox/      … 通知文(.txt) / 集計サマリ(.json) の出力先
└─ processed/   … 処理に成功した元CSVの退避先（--move-processed 使用時）
```

- `--move-processed` を付けると、**処理に成功した元CSVだけ**を `--processed-dir` へ移動する。
  これにより inbox に未処理 CSV だけが残り、同じ CSV の二重処理を防げる。
- 退避先フォルダが無ければ自動作成する。元のファイル名はそのまま保持する。
- 退避先に同名ファイルがある場合は、拡張子の前にタイムスタンプ接尾辞を付けて退避する
  （例: `report.csv` → `report_20260622_143925.csv`）。
- **検証エラー（必須列不足など）や予期しないエラーのときは移動しない**（元CSVは inbox に残る）。

### 共有フォルダでの実行例（UNC パス）

```powershell
cd "$env:USERPROFILE\Documents\Projects\multi-multi-os"

$base = "\\192.168.121.14\Public2\Supervisor\マルチ\シフト進捗＆PJR用\通話呼詳細エクスポート"

python scripts/run_ct_e1_call_loss_check.py `
    --inbox "$base\inbox" `
    --outbox "$base\outbox" `
    --data-dir "$base" `
    --processed-dir "$base\processed" `
    --move-processed
```

### 確定ラッパー: `scripts/Run-CtE1YoshikeiCallLoss.ps1`

ヨシケイ4スキルグループ向けに、確認済みの実行コマンドを固定化した PowerShell ラッパー。
中身は上記 CLI を共有フォルダに対して呼ぶだけ（ログイン自動化・GUI自動化・Teams送信はしない）。

固定している内容:

- 共有ベース: `\\192.168.121.14\Public2\Supervisor\マルチ\シフト進捗＆PJR用\通話呼詳細エクスポート`
- `--inbox` / `--outbox` / `--data-dir` / `--processed-dir` を上記ベース配下に設定
- `--move-processed`（処理成功した元CSVのみ `processed/` へ退避）
- `--threshold 1`
- `--target-skill-group` を以下の4つで指定:
  - `ヨシケイ新潟 お客様相談センター0342361014 着信`
  - `ヨシケイ東京 お客様相談センター0342361015 着信`
  - `ヨシケイ横浜 一次受付業務0342361012 着信`
  - `ヨシケイ滋賀 お客様相談センター0342361013 着信`

挙動:

- 実行時にタイムスタンプ付きヘッダーをコンソールへ表示する。
- 内部 Python CLI の終了コードをそのまま返す（0/1/2/3）。
- スクリプト先頭で自動的にリポジトリ直下へ移動する（どこから呼んでもよい）。
- 日本語リテラルを含むため **UTF-8 (BOM 付き)** で保存している。
  Windows PowerShell 5.1 が cp932 と誤認するのを防ぐため、BOM を外さないこと。

#### 手動実行

```powershell
# どのフォルダからでも可（スクリプトが自動でリポジトリ直下へ移動する）
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Run-CtE1YoshikeiCallLoss.ps1

# 終了コードの確認
echo $LASTEXITCODE
```

> ⚠️ このラッパーは本番の共有フォルダ（UNC）に対して実行され、`--move-processed` により
> 処理に成功した元CSVを `inbox/` から `processed/` へ移動する。実行前に共有フォルダへ
> アクセスできること、`inbox/` に処理対象CSVが揃っていることを確認すること。

### 文字コードについて（実行ログの文字化け対策）

- `run_log.jsonl` は常に **UTF-8** で書き出される（実際のWindowsファイル名を文字化けなく保持する）。
- Windows 標準ツールは UTF-8 を cp932 と誤認して文字化け表示することがある。閲覧時は UTF-8 を指定する:
  `Get-Content "$base\run_log.jsonl" -Encoding utf8`
- CLI 自身の標準出力 / 標準エラーも UTF-8 に固定しているため、`>` でファイルへリダイレクトした
  実行ログも UTF-8 として正しく保存される。

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
| `--processed-dir PATH` | 処理済みCSVの退避先（`--move-processed` と併用） |
| `--move-processed` | 処理成功後に元CSVを `--processed-dir` へ移動（`--processed-dir` 必須） |

引数なしでも動作する（inbox の最新 CSV を選ぶ）。

### 終了コード

| コード | 意味 |
| --- | --- |
| 0 | 成功 |
| 1 | CSV が見つからない |
| 2 | CSV 読込 / 必須列 / 業務エラー / 引数の不整合（`--move-processed` に `--processed-dir` 無し） |
| 3 | 予期しないエラー（処理済みCSVの移動失敗を含む） |

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

**前提: Task Scheduler への登録は、共有フォルダ（UNC パス）での手動テストが通ってから行う。**
具体的には、上記「共有フォルダでの実行例」を手動で実行し、

- 4スキルグループの集計・通知文プレビューが期待どおり出力されること
- `outbox/` に `.txt` / `.json` が作られること
- `--move-processed` で元CSVが `processed/` へ退避されること
- `run_log.jsonl` が UTF-8 で正しく追記されること（文字化けしないこと）

を確認できてから、はじめてスケジューラ登録を検討する。

1. 実行コマンドは確定ラッパー `scripts/Run-CtE1YoshikeiCallLoss.ps1` をそのまま使う
   （例: 18:00 / 20:00 / 21:00 の呼損確認）。
2. 事前に CT-e1 からの CSV エクスポートを共有フォルダの `inbox/` に置く運用を確定する
   （CSV 取得自体の自動化は本リポジトリの対象外）。
3. 成否は終了コードで監視する。出力 `.txt` / `.json` を確認用に残す。
4. Teams 本送信が必要になった場合は、別タスクとして明示依頼の上で追加する
   （本 CLI は通知文プレビューの生成までに留める）。

### Task Scheduler 登録プラン（明示依頼後に実施）

> ⚠️ **重要: タスクを実行する Windows ユーザーが UNC 共有
> （`\\192.168.121.14\Public2\...`）にアクセスできることが必須。**
> Task Scheduler の「ユーザーがログオンしているかどうかにかかわらず実行する」設定では、
> ログオンセッションが無いため共有ドライブのマッピングやネットワーク資格情報が
> 効かず、`inbox/` を読めずに失敗することがある。次の点を満たすこと:
> - 実行アカウントが当該共有への読み書き権限を持つドメイン/ローカルユーザーであること。
> - 認証情報の保存（資格情報マネージャー）またはサービスアカウントで UNC に到達できること。
> - 可能なら登録前に、その実行アカウントで手動ラッパーが成功することを確認する。

登録例（明示依頼を受けてから実行する。本段階では登録しない）:

```powershell
# 例: 平日 18:00 に実行（実行アカウント・権限は上記の警告に従って指定すること）
$action  = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$env:USERPROFILE\Documents\Projects\multi-multi-os\scripts\Run-CtE1YoshikeiCallLoss.ps1`""
$trigger = New-ScheduledTaskTrigger -Daily -At 18:00
# Register-ScheduledTask -TaskName "CtE1_Yoshikei_CallLoss_1800" -Action $action -Trigger $trigger -RunLevel Highest
```

- 18:00 / 20:00 / 21:00 のように時刻別タスクを分けると、しきい値や対象を時刻ごとに調整しやすい。
- 成否はタスクの「前回の実行結果」（= CLI 終了コード）で監視できる。
- `run_log.jsonl` と `outbox/` を後追い確認用に残す。

## 検証

```powershell
cd "$env:USERPROFILE\Documents\Projects\multi-multi-os"
python -m compileall app.py src pages scripts
pytest
git status --short
```

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

- 画面ロック中の実行確認
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
