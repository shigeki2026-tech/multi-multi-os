# multi-multi-os / CT-e1 応答率速報 引き継ぎ 2026-06-26

## 結論

本線は `通話呼詳細V3.5(CSV)` を既存の `応答率速報` に取り込み、期間・業務グループ・個別回線・全回線・放棄秒を指定して、入電数・応答数・呼損数・応答率を確認する運用。

旧 `CT-e1 Yoshikei Call Loss` スケジュールタスクは応答率速報の更新経路ではない。現時点では無効化しない。

## 確定した実装

- `pages/05_応答率速報.py`
  - 応答率閲覧タブを先頭へ移動。
  - 業務判断用UIに変更。
  - 期間開始・期間終了を常時表示。
  - 放棄秒を単独選択。
  - 回線種別を `業務グループ / 個別回線 / 全回線` に分離。
  - 個別回線は巨大プルダウンをやめ、検索入力後に候補最大30件だけ表示。
  - メイン画面から放棄秒ごとの比較表を撤去。
  - KPIは `入電数 / 応答数 / 呼損数 / 応答率` の4枚。

## GitHub commits

- `7a09597 Refine answer rate dashboard UI`
- `4000600 Document AI working rules`
- `84e3aeb Add CT-e1 schedule task audit script`

## スケジュールタスク監査結果

`script/audit_ct_e1_schedule_tasks.ps1` ではなく、実ファイルは以下。

- `scripts/audit_ct_e1_schedule_tasks.ps1`

実行結果では以下3件が存在。

- `CT-e1 Yoshikei Call Loss 18-05` / Ready / LastTaskResult 0 / NextRunTime 18:05
- `CT-e1 Yoshikei Call Loss 20-05` / Ready / LastTaskResult 0 / NextRunTime 20:05
- `CT-e1 Yoshikei Call Loss 21-05` / Ready / LastTaskResult 0 / NextRunTime 21:05

判定: これらは旧Call Loss系。応答率速報の更新経路ではない。現時点で無効化しない。

## ユーザー作業ルール

- 回答だけで終わらせず、必ず次のアクションを提示する。
- PowerShellを何度も人手でコピペさせない。
- 修正は可能な限りGitHub側で行い、ユーザー側は最後の `git pull` と確認だけに寄せる。
- スクショ要求を連発しない。確認点を絞る。

## 次のアクション

1. ローカルで `git pull --ff-only` 済みなら、画面の最終確認だけ。
2. 応答率速報画面で以下が業務上OKか判断。
   - 期間指定
   - 業務グループ
   - 個別回線検索
   - 全回線
   - 放棄秒
   - KPI 4枚
3. OKなら次はテスト・状態確認・必要なら最終コミット確認へ進む。

## 禁止

- 旧Call Lossタスクを本線へ戻さない。
- 座標RPAに戻らない。
- リアルタイム放棄呼一覧V3を主データソースにしない。
- 07_呼詳細作成を触らない。
