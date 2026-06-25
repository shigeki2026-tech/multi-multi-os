# CT-e1 呼損チェック CSV配置SOP

更新日: 2026-06-25

## 目的

CT-e1の通話呼詳細CSVを使い、ヨシケイ4拠点の呼損確認を安定運用する。

## 共有フォルダ

ベース:

    \\192.168.121.14\Public2\Supervisor\マルチ\シフト進捗＆PJR用\通話呼詳細エクスポート

配下:

    inbox      : 処理前CSVを置く
    outbox     : txt/json出力先
    processed  : 処理済みCSVの移動先
    run_log.jsonl : 処理履歴

## 本番タスク

登録済みタスク:

    CT-e1 Yoshikei Call Loss 18-05
    CT-e1 Yoshikei Call Loss 20-05
    CT-e1 Yoshikei Call Loss 21-05

実行時刻:

    18:05
    20:05
    21:05

Task Scheduler設定は InteractiveToken。
ログオン中のユーザーセッション前提。
ログオフ中の完全無人実行は未検証。

## CSV配置ルール

各確認時刻ごとに、CT-e1から最新の通話呼詳細CSVを出力し、実行前に inbox へ置く。

推奨:

    18時確認用CSV → 18:02までに inbox へ置く
    20時確認用CSV → 20:02までに inbox へ置く
    21時確認用CSV → 21:02までに inbox へ置く

1つのCSVを3回使い回さない。
処理成功後、CSVは processed へ移動される。

## CSVなしの場合

2026-06-25 commit 51a2075 以降、CSVなしは異常ではなく正常空振り。

    CSVなし
    → run_log.jsonl に status=no_csv を記録
    → exit 0
    → Task Scheduler LastTaskResult = 0

## 成功判定

CSVあり処理成功時:

    LastTaskResult = 0
    inbox      : CSVが消える
    processed  : CSVが移動される
    outbox     : txt/jsonが作成される
    run_log    : source=cli の行が追加される

## 検証済み事実

2026-06-25確認済み:

    CSVなし wrapper単体:
      ExitCode = 0
      run_log に status=no_csv 追記

    CSVなし Task Scheduler経由:
      LastTaskResult = 0
      run_log に status=no_csv 追記

    画面ロック中 Task Scheduler経由:
      LastTaskResult = 0
      run_log に status=no_csv at 2026-06-25T13:44:01 追記
    CSVあり Task Scheduler経由:
      入力CSV: 通話呼詳細V3.5(CSV)_20260625131513.csv
      total_rows: 89356
      outbound_excluded: 23823
      abandon_count: 94
      alert_count: 4
      出力: ct_e1_call_loss_20260625_132514.txt/json
      processed移動: 成功

## 手動検証ルール

18:05 / 20:05 / 21:05 を待つ必要はない。
検証時は一時タスクを作成し、Start-ScheduledTaskで即時起動する。
Runningが終わるまで待ってから判定する。

禁止:

    本番タスクの時刻を不用意に変更しない
    固定秒数だけで完了判定しない
    Running中の一時タスクを削除しない

## 未完了

    ログオフ中実行の検証
    失敗通知または日次確認SOP
    Task Scheduler XML保存要否判断
    リアルタイム放棄呼.xls対応要否判断

## 禁止事項

    git add . 禁止
    DB / CSV / xls / xlsx / txt / json / run_log / backup をcommitしない
    CT-e1ログイン自動化へ進まない
    GUI自動化へ進まない
    非公開API / Cookie / token に触らない
    複数PCで同じinboxを叩かない
    本番タスクを不用意に変更しない
