#Requires -Version 5.1

param(
    [string]$CsvPath
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
Set-Location -LiteralPath $repoRoot

$pythonScript = Join-Path $scriptDir "import_ct_e1_cdr_to_ui.py"
$base = Join-Path $repoRoot "data\ct_e1"
$inbox = Join-Path $base "inbox"
$processed = Join-Path $base "processed"
$today = Get-Date -Format "yyyyMMdd"

if (-not (Test-Path -LiteralPath $pythonScript)) {
    throw "UI取込Pythonがありません: $pythonScript"
}

if ([string]::IsNullOrWhiteSpace($CsvPath)) {
    $candidates = @()

    foreach ($dir in @($inbox, $processed)) {
        if (Test-Path -LiteralPath $dir) {
            $candidates += @(
                Get-ChildItem -LiteralPath $dir -File -Filter "*.csv" -ErrorAction SilentlyContinue |
                    Where-Object { $_.Name -match "_$today\d{6}\.csv$" }
            )
        }
    }

    $target = $candidates |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($null -eq $target) {
        throw "本日CSVがinbox/processedにありません。"
    }

    $CsvPath = $target.FullName
}

$csv = Get-Item -LiteralPath $CsvPath -ErrorAction Stop

if ($csv.Length -le 0) {
    throw "CSVが0バイトです: $($csv.FullName)"
}

$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (Test-Path -LiteralPath $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonCommand = Get-Command python -ErrorAction Stop
    $pythonExe = $pythonCommand.Source
}

Write-Host "============================================================"
Write-Host "CT-e1 CDR -> 応答率UI 自動取込"
Write-Host "CSV   : $($csv.FullName)"
Write-Host "Bytes : $($csv.Length)"
Write-Host "Python: $pythonExe"
Write-Host "============================================================"

& $pythonExe `
    $pythonScript `
    --csv $csv.FullName `
    --replace-existing

$code = $LASTEXITCODE

if ($code -ne 0) {
    throw "応答率UI取込失敗: exit=$code"
}

Write-Host ""
Write-Host "RESULT: CT_E1_CDR_UI_WRAPPER_SUCCESS"
exit 0