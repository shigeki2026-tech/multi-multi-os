# CT-e1 Task Scheduler Restore Notes

更新日: 2026-06-25

## 目的

CT-e1呼損チェック用のWindows Task Scheduler定義をGit管理する。

Task Scheduler設定はWindowsローカル状態であり、Gitには自動保存されない。
PC再構築・タスク削除・別PC移行時に消えるため、XMLを保存する。

## 保存済みタスク

    scripts/task_scheduler/ct_e1_yoshikei_call_loss_18-05.xml
    scripts/task_scheduler/ct_e1_yoshikei_call_loss_20-05.xml
    scripts/task_scheduler/ct_e1_yoshikei_call_loss_21-05.xml

## 登録済みタスク名

    CT-e1 Yoshikei Call Loss 18-05
    CT-e1 Yoshikei Call Loss 20-05
    CT-e1 Yoshikei Call Loss 21-05

## 現在の前提

    LogonType = InteractiveToken
    RunLevel  = Limited相当

ログオン中のユーザーセッションが前提。
画面ロック中の実行は2026-06-25に確認済み。
ログオフ中の完全無人実行は未検証。

## 復元例

必要時のみ実行する。

    cd "$env:USERPROFILE\Documents\Projects\multi-multi-os"

    schtasks /create /tn "CT-e1 Yoshikei Call Loss 18-05" /xml ".\scripts\task_scheduler\ct_e1_yoshikei_call_loss_18-05.xml" /f
    schtasks /create /tn "CT-e1 Yoshikei Call Loss 20-05" /xml ".\scripts\task_scheduler\ct_e1_yoshikei_call_loss_20-05.xml" /f
    schtasks /create /tn "CT-e1 Yoshikei Call Loss 21-05" /xml ".\scripts\task_scheduler\ct_e1_yoshikei_call_loss_21-05.xml" /f

## 注意

XMLにはUserId/SIDやローカルパスが含まれる。
通常パスワードは含まれない。
別PC移行時はUserIdやパス差異を確認する。
