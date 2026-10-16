param ([switch] $Debug)
$CMK_VERSION = "3.0.0b1"
## VEEAM Backups
## This powershell script needs to be run with the 64bit powershell
## and thus from a 64bit check_mk agent
## If a 64 bit check_mk agent is available it just needs to be renamed with
## the extension .ps1
## If only a 32bit  check_mk agent is available it needs to be relocated to a
## directory given in veeam_backup_status.bat and the .bat file needs to be
## started by the check_mk agent instead.

$pshost = Get-Host
$pswindow = $pshost.ui.rawui

$newsize = $pswindow.buffersize
$newsize.height = 300
$newsize.width = 150
$pswindow.buffersize = $newsize

## -- start of the code which may switch powershell --
## Code below may been tested separately
if ($Debug) {
    $DebugPreference = 'Continue'
}

$borderVersion = 13
try {
    # works only if process is running, normally it's ok
    $veeamVersion = [int](Get-Process | where { $_.Name -like "*Veeam.Backup.Service*" }).ProductVersion.Substring(0, 2)
}
catch {
    Write-Debug "Could not determine Veeam version, assuming v13"
    $veeamVersion = $borderVersion
}

$isNewVeeam = $veeamVersion -ge $borderVersion
$isNewPowershell = $PSVersionTable.PSVersion.Major -ge 7

try {
    if ($isNewVeeam -and -not( $isNewPowershell) ) {
        Write-Debug "Switch Powershell 7(core)"
        pwsh $PSCommandPath @PSBoundParameters
        exit 0
    }

    if (-not ($isNewVeeam) -and $isNewPowershell) {
        Write-Debug "Switch to Powershell 5"
        powershell $PSCommandPath @PSBoundParameters
        exit 0
    }

    Write-Debug "Staying in Powershell $($PSVersionTable.PSVersion.Major)"

}
catch {
    if ($Debug) {
        Write-Debug "Could not execute required PowerShell"
    }
    exit 1
}
## -- end of the code which may switch powershell --


## Situation with powershell ascii and code page in Windows is not uniform
## We do not send UTF8 BOM: we call [Text.UTF8Encoding]::UTF8 functionally the same as [Text.UTF8Encoding]::new($false)
## See:
## https://devblogs.microsoft.com/powershell/outputencoding-to-the-rescue/
## https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_character_encoding?view=powershell-7.5
## https://www.ibm.com/docs/en/noi/1.6.13?topic=chs-ssh-automation-action-output-powershell-shows-garbled-multi-byte-characters
$OutputEncoding = [Console]::OutputEncoding = [Text.UTF8Encoding]::UTF8

# Get Information from veeam backup and replication in cmk-friendly format
# V0.9

# Load Veeam Backup and Replication Powershell Snapin
try {
    Import-Module Veeam.Backup.PowerShell -ErrorAction Stop -DisableNameChecking
}
catch {
    try {
        Add-PSSnapin VeeamPSSnapIn -ErrorAction Stop
    }
    catch {
        if ($Debug) {
            Write-Host "No Veeam powershell modules could be loaded"
        }
        exit 1
    }
}


try {
    $tapeJobs = Get-VBRTapeJob
    Write-Host "<<<veeam_tapejobs:sep(124)>>>"
    Write-Host "JobName|JobID|LastResult|LastState"
    foreach ($tapeJob in $tapeJobs) {
        $jobName = $tapeJob.Name
        $jobID = $tapeJob.Id
        $lastResult = $tapeJob.LastResult
        $lastState = $tapeJob.LastState
        Write-Host "$jobName|$jobID|$lastResult|$lastState"
    }


    try {
        $cdpjobs = Get-VBRCDPPolicy | Select-Object Id, Name, NextRun, PolicyState, LastResult
    }
    catch {
        Write-Host "CDP jobs not supported"
        $cdpjobs = $false
    }

    if ( $cdpjobs ) {
        try {
            $cdpReplicas = @(Get-VBRCDPReplica -ErrorAction Stop)
        }
        catch {
            $cdpReplicas = @()
        }

        $myCdpJobsText = "<<<veeam_cdp_jobs:sep(124)>>>`n"

        foreach ($mycdpjobs in $cdpjobs) {
            $MyCdpJobsName = $mycdpjobs.Name -replace "\'", "_" -replace " ", "_"

            $MyCdpJobsNextRun = $mycdpjobs.NextRun
            if ($MyCdpJobsNextRun -ne $null) {
                $MyCdpJobsNextRun = ([DateTimeOffset]$MyCdpJobsNextRun).ToUnixTimeSeconds()
            }
            else {
                $MyCdpJobsNextRun = "null"
            }

            $MyCdpJobsPolicyState = $mycdpjobs.PolicyState

            # The replica lagging behind the most determines how current the policy is
            $MyCdpJobsLastSync = ($cdpReplicas | Where-Object { $_.JobId -eq $mycdpjobs.Id -and $_.LastPointCreationTime -ne $null } | ForEach-Object { $_.LastPointCreationTime } | Sort-Object | Select-Object -First 1)
            if ($MyCdpJobsLastSync -ne $null) {
                $MyCdpJobsLastSync = ([DateTimeOffset]$MyCdpJobsLastSync).ToUnixTimeSeconds()
            }
            else {
                $MyCdpJobsLastSync = "null"
            }

            $MyCdpJobsLastResult = $mycdpjobs.LastResult
            if ($MyCdpJobsLastResult -eq $null) {
                $MyCdpJobsLastResult = "null"
            }

            $myCdpJobsText = "$myCdpJobsText" + "$MyCdpJobsName" + "|" + "$MyCdpJobsNextRun" + "|" + "$MyCdpJobsPolicyState" + "|" + "$MyCdpJobsLastSync" + "|" + "$MyCdpJobsLastResult" + "`n"
        }

        Write-Host $myCdpJobsText
    }

    $myJobsText = "<<<veeam_jobs:sep(9)>>>`n"
    $myTaskText = ""

    $myBackupJobs = Get-VBRJob -WarningAction SilentlyContinue | where { $_.IsScheduleEnabled -eq $true }

    foreach ($myJob in $myBackupJobs) {
        $myJobName = $myJob.Name -replace "\'", "_" -replace " ", "_"

        $myJobType = $myjob.JobType

        $myJobLastState = $myJob.GetLastState()

        $myJobLastResult = $myJob.GetLastResult()

        $myJobLastSession = $myJob.FindLastSession()

        $myJobCreationTime = $myJobLastSession.CreationTime |  Get-Date -Format "dd.MM.yyyy HH\:mm\:ss"  -ErrorAction SilentlyContinue

        $myJobEndTime = $myJobLastSession.EndTime |  Get-Date -Format "dd.MM.yyyy HH\:mm\:ss"  -ErrorAction SilentlyContinue

        $myJobsText = "$myJobsText" + "$myJobName" + "`t" + "$myJobType" + "`t" + "$myJobLastState" + "`t" + "$myJobLastResult" + "`t" + "$myJobCreationTime" + "`t" + "$myJobEndTime" + "`n"

        # For Non Backup Jobs (Replicas) we bail out
        # because we are interested in the status of the original backup but
        # for replicas the overall job state is all we need.
        # Monitor also jobs with the EpAgentBackup job type.
        if ($myJob.IsBackup -eq $false -and $myJob.JobType -ne "EpAgentBackup") {
            continue
        }

        # Each backup job has a number of tasks which were executed (VMs which were processed)
        # Get all Tasks of the  L A S T  backup session
        # Caution: Each backup job MAY have run SEVERAL times for retries,
        # thats why we need all sessions related to the last one if its a retry
        $sessions = @($myJobLastSession)
        if ($myJobLastSession.IsRetryMode) {
            $sessions = $myJobLastSession.GetOriginalAndRetrySessions($TRUE)
        }

        $myJobLastSessionTasks = $sessions | Get-VBRTaskSession  -ErrorAction SilentlyContinue

        foreach ($myTask in $myJobLastSessionTasks) {
            $myTaskName = $myTask.Name -replace "[^ -x7e]" -replace " ", "_"

            $myTaskText = "$myTaskText" + "<<<<" + "$myTaskName" + ">>>>" + "`n"

            $myTaskText = "$myTaskText" + "<<<" + "veeam_client:sep(9)" + ">>>" + "`n"

            $myTaskStatus = $myTask.Status

            $myTaskText = "$myTaskText" + "Status" + "`t" + "$myTaskStatus" + "`n"

            $myTaskText = "$myTaskText" + "JobName" + "`t" + "$myJobName" + "`n"

            $myTaskTotalSize = $myTask.Progress.TotalSize

            $myTaskText = "$myTaskText" + "TotalSizeByte" + "`t" + "$myTaskTotalSize" + "`n"

            $myTaskReadSize = $myTask.Progress.ReadSize

            $myTaskText = "$myTaskText" + "ReadSizeByte" + "`t" + "$myTaskReadSize" + "`n"

            $myTaskTransferedSize = $myTask.Progress.TransferedSize

            $myTaskText = "$myTaskText" + "TransferedSizeByte" + "`t" + "$myTaskTransferedSize" + "`n"

            # Starting from Version 9.5U3 StartTime is not supported anymore
            if ($myTask.Progress.StartTime -eq $Null) {
                $myTaskStartTime = $myTask.Progress.StartTimeLocal
            }
            else {
                $myTaskStartTime = $myTask.Progress.StartTime
            }
            $myTaskStartTime = $myTaskStartTime | Get-Date -Format "dd.MM.yyyy HH\:mm\:ss" -ErrorAction SilentlyContinue

            $myTaskText = "$myTaskText" + "StartTime" + "`t" + "$myTaskStartTime" + "`n"

            # Starting from Version 9.5U3 StopTime is not supported anymore
            if ($myTask.Progress.StopTime -eq $Null) {
                $myTaskStopTime = $myTask.Progress.StopTimeLocal
            }
            else {
                $myTaskStopTime = $myTask.Progress.StopTime
            }
            $lastBackupAge = New-TimeSpan -Start $myTaskStopTime -End (Get-Date) -ErrorAction SilentlyContinue

            $myTaskText = "$myTaskText" + "LastBackupAge" + "`t" + "$($lastBackupAge.TotalSeconds)" + "`n"

            # Result is a value of type System.TimeStamp. I'm sure there is a more elegant way of formatting the output:
            $myTaskDuration = "" + "{0:D2}" -f $myTask.Progress.duration.Days + ":" + "{0:D2}" -f $myTask.Progress.duration.Hours + ":" + "{0:D2}" -f $myTask.Progress.duration.Minutes + ":" + "{0:D2}" -f $myTask.Progress.duration.Seconds

            $myTaskText = "$myTaskText" + "DurationDDHHMMSS" + "`t" + "$myTaskDuration" + "`n"

            $myTaskAvgSpeed = $myTask.Progress.AvgSpeed

            $myTaskText = "$myTaskText" + "AvgSpeedBps" + "`t" + "$myTaskAvgSpeed" + "`n"

            $myTaskDisplayName = $myTask.Progress.DisplayName

            $myTaskText = "$myTaskText" + "DisplayName" + "`t" + "$myTaskDisplayName" + "`n"

            $myBackupHost = Hostname

            $myTaskText = "$myTaskText" + "BackupServer" + "`t" + "$myBackupHost" + "`n"

            $myTaskText = "$myTaskText" + "<<<<" + ">>>>" + "`n"

        }

    }

    Write-Host $myJobsText
    Write-Host $myTaskText

    # The result of a policy managed by the agent only reflects applying the policy.
    # Each protected computer backs up in its own session named "<policy> - <computer>".
    $myPolicyWorkloadsText = "<<<veeam_agent_policy_workloads:sep(9)>>>`n"
    try {
        foreach ($myPolicy in Get-VBRComputerBackupJob -Mode ManagedByAgent -ErrorAction Stop) {
            $myPolicyName = $myPolicy.Name -replace "\'", "_" -replace " ", "_"
            try {
                # Only computers currently protected by the policy, so removed ones do not linger
                $myComputers = foreach ($myBackupObject in $myPolicy.BackupObject) {
                    if ($myBackupObject.GetType().Name -eq "VBRProtectionGroup") {
                        Get-VBRDiscoveredComputer -ProtectionGroup $myBackupObject -ErrorAction Stop | ForEach-Object { $_.Name }
                    }
                    else {
                        $myBackupObject.Name
                    }
                }

                # One query per policy, a running backup has no result yet
                $myFinishedSessions = @{}
                Get-VBRComputerBackupJobSession -Name "$([WildcardPattern]::Escape("$($myPolicy.Name) - "))*" -ErrorAction Stop |
                    Where-Object { $_.State -eq "Stopped" } |
                    Sort-Object CreationTime |
                    ForEach-Object { $myFinishedSessions[$_.Name] = $_ }

                foreach ($myComputer in $myComputers | Sort-Object -Unique) {
                    $myWorkloadName = $myComputer -replace "\'", "_" -replace " ", "_"
                    $myWorkloadSession = $myFinishedSessions["$($myPolicy.Name) - $myComputer"]

                    if ($myWorkloadSession -eq $null) {
                        $myPolicyWorkloadsText = "$myPolicyWorkloadsText" + "computer" + "`t" + "$myPolicyName" + "`t" + "$myWorkloadName" + "`t" + "None" + "`t" + "None" + "`n"
                        continue
                    }

                    $myWorkloadCreationTime = $myWorkloadSession.CreationTime | Get-Date -Format "dd.MM.yyyy HH\:mm\:ss" -ErrorAction SilentlyContinue

                    $myWorkloadEndTime = $myWorkloadSession.EndTime | Get-Date -Format "dd.MM.yyyy HH\:mm\:ss" -ErrorAction SilentlyContinue

                    $myPolicyWorkloadsText = "$myPolicyWorkloadsText" + "computer" + "`t" + "$myPolicyName" + "`t" + "$myWorkloadName" + "`t" + "$($myWorkloadSession.State)" + "`t" + "$($myWorkloadSession.Result)" + "`t" + "$myWorkloadCreationTime" + "`t" + "$myWorkloadEndTime" + "`n"
                }
            }
            catch {
                $myPolicyWorkloadsText = "$myPolicyWorkloadsText" + "error" + "`t" + "$myPolicyName" + "`t" + ("$_" -replace "\s+", " ") + "`n"
            }
        }
    }
    catch {
        # Applies to all policies managed by the agent
        $myPolicyWorkloadsText = "$myPolicyWorkloadsText" + "error" + "`t" + "*" + "`t" + ("$_" -replace "\s+", " ") + "`n"
    }
    Write-Host $myPolicyWorkloadsText
}

catch {
    Write-Error "Totally unexpected and unhandled error occurred:`n$($_ | Out-String)"
    break
}
