$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

Write-Host "=== CT-e1 schedule task audit ==="
Write-Host "Purpose: separate legacy Call Loss tasks from the current answer-rate workflow."
Write-Host "Current workflow: CT-e1 通話呼詳細CSV -> 応答率速報 CDR取込 -> 応答率閲覧"
Write-Host "Legacy Call Loss tasks do not update 応答率速報."
Write-Host "This script is read-only. It does not change scheduled tasks."
Write-Host ""

function Test-LegacyCallLossTaskName {
    param([string]$Name)
    return ($Name -like "*CT-e1*Call Loss*" -or $Name -like "*Yoshikei Call Loss*")
}

$allTasks = Get-ScheduledTask
$targets = @()
foreach ($task in $allTasks) {
    $fullName = "$($task.TaskPath)$($task.TaskName)"
    if (Test-LegacyCallLossTaskName $fullName) {
        $targets += $task
    }
}

if (-not $targets -or $targets.Count -eq 0) {
    Write-Host "No legacy CT-e1/Yoshikei Call Loss scheduled tasks found."
    exit 0
}

$rows = foreach ($task in $targets) {
    $info = $null
    try {
        $info = Get-ScheduledTaskInfo -TaskName $task.TaskName -TaskPath $task.TaskPath
    } catch {
        Write-Warning "Could not read task info: $($task.TaskPath)$($task.TaskName) :: $($_.Exception.Message)"
    }

    [PSCustomObject]@{
        TaskName       = $task.TaskName
        TaskPath       = $task.TaskPath
        State          = $task.State
        LastRunTime    = if ($info) { $info.LastRunTime } else { $null }
        LastTaskResult = if ($info) { $info.LastTaskResult } else { $null }
        NextRunTime    = if ($info) { $info.NextRunTime } else { $null }
    }
}

$rows | Format-Table -AutoSize

Write-Host ""
Write-Host "Judgment: these are legacy Call Loss tasks. They are not the data path for 応答率速報."
Write-Host "No changes made."
