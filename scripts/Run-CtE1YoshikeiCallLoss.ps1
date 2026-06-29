#Requires -Version 5.1

<#
.SYNOPSIS
    ヨシケイ4スキルグループの CT-e1 呼損チェックを、ローカル data/ct_e1 の当日CSVだけで実行するラッパー。

.DESCRIPTION
    外部CT-e1 RPAが保存した当日CSVだけを data/ct_e1/inbox から処理する。
    過去CSVが inbox に残っていても処理しない。
    CSVなしは正常な空振りとして run_log.jsonl に no_csv を残して exit 0。
#>

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Split-Path -Parent $scriptDir
Set-Location -LiteralPath $repoRoot

$base = Join-Path $repoRoot "data\ct_e1"
$inbox = Join-Path $base "inbox"
$outbox = Join-Path $base "outbox"
$processed = Join-Path $base "processed"
$runLog = Join-Path $base "run_log.jsonl"
$today = Get-Date -Format "yyyyMMdd"

New-Item -ItemType Directory -Force $base | Out-Null
New-Item -ItemType Directory -Force $inbox | Out-Null
New-Item -ItemType Directory -Force $outbox | Out-Null
New-Item -ItemType Directory -Force $processed | Out-Null

$csvFiles = @(Get-ChildItem -LiteralPath $inbox -Filter "*.csv" -File -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match "_$today\d{6}\.csv$" })

if ($csvFiles.Count -eq 0) {
  $noCsvLog = [ordered]@{
    source = "wrapper"
    status = "no_csv"
    message = "No TODAY CSV files found in local inbox. Treated as normal no-op."
    inbox = $inbox
    expected_date = $today
    at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")
  }

  $noCsvLog | ConvertTo-Json -Compress | Add-Content -Path $runLog -Encoding UTF8
  exit 0
}

$targetCsv = $csvFiles | Sort-Object LastWriteTime -Descending | Select-Object -First 1

$skillGroups = @(
  "ヨシケイ新潟 お客様相談センター0342361014 着信",
  "ヨシケイ東京 お客様相談センター0342361015 着信",
  "ヨシケイ横浜 一次受付業務0342361012 着信",
  "ヨシケイ滋賀 お客様相談センター0342361013 着信"
)

$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "============================================================"
Write-Host "CT-e1 呼損チェック（ヨシケイ4スキルグループ）"
Write-Host ("実行時刻 : {0}" -f $stamp)
Write-Host ("リポジトリ: {0}" -f $repoRoot)
Write-Host ("ローカルベース: {0}" -f $base)
Write-Host ("対象日CSV : {0}" -f $targetCsv.FullName)
Write-Host ("outbox    : {0}" -f $outbox)
Write-Host ("processed : {0}" -f $processed)
Write-Host ("しきい値 : 1 / 移動: 有効 (--move-processed)")
Write-Host "============================================================"

$arguments = @(
  "scripts/run_ct_e1_call_loss_check.py",
  "--csv",           $targetCsv.FullName,
  "--outbox",        $outbox,
  "--data-dir",      $base,
  "--processed-dir", $processed,
  "--move-processed",
  "--threshold",     "1"
)

foreach ($g in $skillGroups) {
  $arguments += "--target-skill-group"
  $arguments += $g
}

python @arguments
$code = $LASTEXITCODE

Write-Host "------------------------------------------------------------"
Write-Host ("[exit] Python CLI 終了コード: {0}" -f $code)
exit $code
