#Requires -Version 5.1
<#
.SYNOPSIS
    ヨシケイ4スキルグループの CT-e1 呼損チェックを、共有フォルダ運用で実行する確定ラッパー。

.DESCRIPTION
    確認済みの手動コマンドを固定化したもの。中身は既存の決定論 CLI
    （scripts/run_ct_e1_call_loss_check.py）を共有フォルダ（UNC パス）に対して呼ぶだけ。

    やらないこと（方針・厳守）:
    - CT-e1 への自動ログイン・GUI自動化・非公開API/Cookie/token 利用はしない。
    - Teams 本送信はしない（通知文プレビューの生成・保存に留める）。
    - DB スキーマは変更しない。
    - Windows Task Scheduler への登録はしない（手動実行のみ。登録手順は docs を参照）。

    処理に成功した元CSVだけが processed/ へ退避される（--move-processed）。
    検証エラー時は移動されず、元CSVは inbox に残る。

    ※ このファイルは日本語リテラルを含むため UTF-8 (BOM 付き) で保存している。
       Windows PowerShell 5.1 が cp932 と誤認して文字化けするのを防ぐため、BOM を外さないこと。

.NOTES
    終了コードは内部 Python CLI のものをそのまま返す:
        0 成功 / 1 CSVなし / 2 業務・引数エラー / 3 予期しないエラー（移動失敗含む）
#>

$ErrorActionPreference = "Stop"

# --- リポジトリ直下へ移動（このスクリプトは scripts/ 配下にある） ---
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Split-Path -Parent $scriptDir
Set-Location -LiteralPath $repoRoot

# --- 共有フォルダ（UNC）のベースパス ---
$base = "\\192.168.121.14\Public2\Supervisor\マルチ\シフト進捗＆PJR用\通話呼詳細エクスポート"

# --- ヨシケイ対象4スキルグループ ---
$skillGroups = @(
    "ヨシケイ新潟 お客様相談センター0342361014 着信",
    "ヨシケイ東京 お客様相談センター0342361015 着信",
    "ヨシケイ横浜 一次受付業務0342361012 着信",
    "ヨシケイ滋賀 お客様相談センター0342361013 着信"
)

# --- コンソールヘッダー（タイムスタンプ付き） ---
$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "============================================================"
Write-Host "CT-e1 呼損チェック（ヨシケイ4スキルグループ）"
Write-Host ("実行時刻 : {0}" -f $stamp)
Write-Host ("リポジトリ: {0}" -f $repoRoot)
Write-Host ("共有ベース: {0}" -f $base)
Write-Host ("しきい値 : 1  / 移動    : 有効 (--move-processed)")
Write-Host "============================================================"

# --- Python CLI 引数の組み立て ---
$arguments = @(
    "scripts/run_ct_e1_call_loss_check.py",
    "--inbox",         "$base\inbox",
    "--outbox",        "$base\outbox",
    "--data-dir",      "$base",
    "--processed-dir", "$base\processed",
    "--move-processed",
    "--threshold",     "1"
)
foreach ($g in $skillGroups) {
    $arguments += "--target-skill-group"
    $arguments += $g
}

# --- 実行（標準出力/標準エラーはそのまま表示） ---
python @arguments
$code = $LASTEXITCODE

Write-Host "------------------------------------------------------------"
Write-Host ("[exit] Python CLI 終了コード: {0}" -f $code)

# --- Python の終了コードをそのまま返す ---
exit $code
