# CT-e1 呼損チェック 引き継ぎ書

更新日: 2026-06-25
対象リポジトリ: C:\Users\User\Documents\Projects\multi-multi-os

## 0. 現在の結論

CT-e1 呼損チェックは、通話呼詳細CSVを使う範囲では実運用可能な状態まで到達済み。

完了済み:

- CSVありのTask Scheduler経由処理成功
- CSVなしを正常空振り no_csv として exit 0 にする修正
- 画面ロック中のTask Scheduler実行成功
- CSV配置SOP作成
- Task Scheduler XML保存
- 関連docs反映
- GitHub push済み

現時点でこれ以上の開発追加は不要。
次にやるべきことは、実運用でCSVを置く担当・タイミングを守ること。

## 1. 最新HEAD

```text
983d019 Save CT-e1 task scheduler definitions
2039daa Document CT-e1 lock-screen scheduler success
9d1ec22 Add CT-e1 CSV placement SOP
c3d8984 Document CT-e1 call-loss scheduler status
51a2075 Treat missing CT-e1 CSV as no-op
4d8afec Add CT-e1 Yoshikei call-loss wrapper
efd8aa2 Add processed CSV handling to CT-e1 CLI
324e279 Add CT-e1 call-loss CLI wrapper for saved CSVs
```

git status はクリーン確認済み。

## 2. 対象パス

リポジトリ:

```text
C:\Users\User\Documents\Projects\multi-multi-os
```

共有フォルダ:

```text
\\192.168.121.14\Public2\Supervisor\マルチ\シフト進捗＆PJR用\通話呼詳細エクスポート
```

配下:

```text
inbox
outbox
processed
run_log.jsonl
```

## 3. 本番タスク

登録済みTask Scheduler:

```text
CT-e1 Yoshikei Call Loss 18-05
CT-e1 Yoshikei Call Loss 20-05
CT-e1 Yoshikei Call Loss 21-05
```

実行時刻:

```text
18:05
20:05
21:05
```

設定:

```text
LogonType = InteractiveToken
RunLevel = Limited相当
```

つまり、ログオン中ユーザーセッション前提。
画面ロック中の実行は確認済み。
ログオフ中の完全無人実行は未検証。

## 4. 処理仕様

入力:

```text
inbox に置かれた 通話呼詳細V3.5(CSV)_*.csv
```

処理:

```text
scripts/Run-CtE1YoshikeiCallLoss.ps1
scripts/run_ct_e1_call_loss_check.py
```

出力:

```text
outbox に ct_e1_call_loss_yyyymmdd_hhmmss.txt
outbox に ct_e1_call_loss_yyyymmdd_hhmmss.json
processed に処理済みCSVを移動
run_log.jsonl に履歴追記
```

重要:

```text
--move-processed 有効
1つのCSVを3回使い回す設計ではない
18:05 / 20:05 / 21:05 それぞれで処理したいなら各時刻前に新しいCSVが必要
```

## 5. 検証済み事実

CSVなし wrapper単体:

```text
ExitCode = 0
run_log に status=no_csv 追記
```

CSVなし Task Scheduler経由:

```text
LastTaskResult = 0
run_log に status=no_csv 追記
```

CSVあり Task Scheduler経由:

```text
入力CSV: 通話呼詳細V3.5(CSV)_20260625131513.csv
total_rows: 89356
outbound_excluded: 23823
abandon_count: 94
alert_count: 4
出力: ct_e1_call_loss_20260625_132514.txt/json
processed移動: 成功
```

画面ロック中 Task Scheduler経由:

```text
一時タスク: CT-e1 Yoshikei Call Loss TEMP LOCK
LastRunTime: 2026/06/25 13:44:00
LastTaskResult: 0
run_log: status=no_csv at 2026-06-25T13:44:01
```

## 6. 保存済みドキュメント

```text
CLAUDE.md
docs/ct_e1_schedule_plan.md
docs/ct_e1_csv_placement_sop.md
docs/ct_e1_task_scheduler_restore.md
```

Task Scheduler XML:

```text
scripts/task_scheduler/ct_e1_yoshikei_call_loss_18-05.xml
scripts/task_scheduler/ct_e1_yoshikei_call_loss_20-05.xml
scripts/task_scheduler/ct_e1_yoshikei_call_loss_21-05.xml
```

## 7. 運用ルール

通常運用:

```text
18時確認用CSV → 18:02までに inbox へ置く
20時確認用CSV → 20:02までに inbox へ置く
21時確認用CSV → 21:02までに inbox へ置く
```

CSVなしの場合:

```text
異常ではない
status=no_csv
LastTaskResult=0
```

CSVありで異常と見る条件:

```text
CSVを置いたのに inbox に残る
outbox が更新されない
processed に移動されない
run_log に source=cli が出ない
LastTaskResult が 0 以外
```

## 8. 禁止事項

```text
git add . 禁止
DB / CSV / xls / xlsx / txt / json / run_log / backup をcommitしない
CT-e1ログイン自動化へ進まない
GUI自動化へ進まない
非公開API / Cookie / token に触らない
複数PCで同じ inbox を叩かない
本番タスクの時刻を不用意に変更しない
固定秒数だけで完了判定しない
Running中の一時タスクを削除しない
```

## 9. 未完了だが今やらないこと

```text
ログオフ中実行の検証
失敗通知または日次確認SOP
リアルタイム放棄呼.xls対応
PowerToys更新
```

ログオフ中実行は InteractiveToken 前提から外れる。
資格情報・UNC到達・S4Uなど別問題になるため、今すぐ触らない。

## 10. 次チャットで最初に確認すること

```powershell
cd "$env:USERPROFILE\Documents\Projects\multi-multi-os"
git status --short
git log --oneline -8
```

期待値:

```text
git status --short は空
HEAD は 983d019 以降
```
