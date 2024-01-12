$CMK_VERSION = "2.3.0b1"

Write-Host "<<<windows_tasks:sep(58):encoding(cp437)>>>"
$tasks = Get-ScheduledTask
foreach ($task in $tasks) {
    $task_name = "$($task.TaskPath.ToString())$($task.TaskName.ToString())"
    $task_info = $task | Get-ScheduledTaskInfo
    if (!$task.TaskPath.StartsWith("\Microsoft")){
        Write-Host "TaskName `t: "$task_name
        Write-Host "Last Run Time `t: "$task_info.LastRunTime
        Write-Host "Next Run Time `t: "$task_info.NextRunTime
        Write-Host "Last Result `t: "$task_info.LastTaskResult
        if ($task.'State' -eq 'Disabled'){
            Write-Host "Scheduled Task State `t: Disabled"
        } else {
            Write-Host "Scheduled Task State `t: Enabled"
        }
        Write-Host ""
    }
}
