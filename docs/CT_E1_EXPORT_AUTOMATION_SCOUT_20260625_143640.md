# CT-e1 CSV出力自動化 調査ログ

更新日: 2026-06-25
目的: CT-e1から通話呼詳細CSVを自動取得して inbox へ置く工程の実装前調査。

## 現在の固定済み範囲

- inbox にCSVが置かれた後の呼損集計は自動化済み。
- Task Scheduler 18:05 / 20:05 / 21:05 は登録済み。
- CSVなしは no_csv で正常終了。
- 画面ロック中の実行は確認済み。

## 今回調査する範囲

- CT-e1 / 通話呼詳細 / CDR / CSV出力に関係する既存ファイル
- ユーザー領域の既存CSV保存場所
- Desktop / Start Menu のショートカット
- Downloads / Documents の通話呼詳細CSV
- 既存リポジトリ内の関連コード・ドキュメント
- Task Scheduler現況

## 出力ファイル

- logs/ct_e1_export_scout_20260625_143640/browser_download_dirs.txt
- logs/ct_e1_export_scout_20260625_143640/environment.txt
- logs/ct_e1_export_scout_20260625_143640/existing_call_detail_csv.txt
- logs/ct_e1_export_scout_20260625_143640/git_state.txt
- logs/ct_e1_export_scout_20260625_143640/repo_search_ct_e1.txt
- logs/ct_e1_export_scout_20260625_143640/shortcut_search.txt
- logs/ct_e1_export_scout_20260625_143640/task_scheduler_ct_e1.txt
- logs/ct_e1_export_scout_20260625_143640/url_file_content_search.txt

## 次に見るべきファイル

1. existing_call_detail_csv.txt
2. shortcut_search.txt
3. url_file_content_search.txt
4. repo_search_ct_e1.txt

## 判定

この調査で、CT-e1の入口URL・ショートカット・CSV保存場所が見つかれば、次はCSV取得工程を作る。
入口が見つからない場合は、手動でCT-e1を開いた状態からウィンドウタイトル・URL・ダウンロード挙動を採取する。
