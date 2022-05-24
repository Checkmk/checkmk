$CMK_VERSION = "2.0.0p26"
## VEEAM Backups
## This powershell script needs to be run with the 64bit powershell
## and thus from a 64bit check_mk agent
## If a 64 bit check_mk agent is available it just needs to be renamed with
## the extension .ps1
## If only a 32bit  check_mk agent is available it needs to be relocated to a
## directory given in veeam_backup_status.bat and the .bat file needs to be
## started by the check_mk agent instead.

$pshost = get-host
$pswindow = $pshost.ui.rawui

$newsize = $pswindow.buffersize
$newsize.height = 300
$newsize.width = 150
$pswindow.buffersize = $newsize

# Get Information from veeam backup and replication in cmk-friendly format
# V0.9

# Load Veeam Backup and Replication Powershell Snapin
try {
    Import-Module Veeam.Backup.PowerShell -ErrorAction Stop
}
catch {
    try {
        Add-PSSnapin VeeamPSSnapIn -ErrorAction Stop
    }
    catch {
        Write-Host "No Veeam powershell modules could be loaded"
        Exit 1
    }
}


try
{
$tapeJobs = Get-VBRTapeJob
write-host "<<<veeam_tapejobs:sep(124)>>>"
write-host "JobName|JobID|LastResult|LastState"
foreach ($tapeJob in $tapeJobs)
    {
        $jobName = $tapeJob.Name
        $jobID = $tapeJob.Id
        $lastResult = $tapeJob.LastResult
        $lastState = $tapeJob.LastState
        write-host "$jobName|$jobID|$lastResult|$lastState"
    }


$myJobsText = "<<<veeam_jobs:sep(9)>>>`n"
$myTaskText = ""

$myBackupJobs = Get-VBRJob | where {$_.IsScheduleEnabled -eq $true }

foreach ($myJob in $myBackupJobs)
    {
	$myJobName = $myJob.Name -replace "\'","_" -replace " ","_"

	$myJobType = $myjob.JobType

	$myJobLastState = $myJob.GetLastState()

	$myJobLastResult = $myJob.GetLastResult()

	$myJobLastSession = $myJob.FindLastSession()

	$myJobCreationTime = $myJobLastSession.CreationTime |  get-date -Format "dd.MM.yyyy HH\:mm\:ss"  -ErrorAction SilentlyContinue

	$myJobEndTime = $myJobLastSession.EndTime |  get-date -Format "dd.MM.yyyy HH\:mm\:ss"  -ErrorAction SilentlyContinue

	$myJobsText = "$myJobsText" + "$myJobName" + "`t" + "$myJobType" + "`t" + "$myJobLastState" + "`t" + "$myJobLastResult" + "`t" + "$myJobCreationTime" + "`t" + "$myJobEndTime" + "`n"

	# For Non Backup Jobs (Replicas) we bail out
	# because we are interested in the status of the original backup but
	# for replicas the overall job state is all we need.
        if ($myJob.IsBackup -eq $false) { continue }

	# Each backup job has a number of tasks which were executed (VMs which were processed)
	# Get all Tasks of the  L A S T  backup session
	# Caution: Each backup job MAY have run SEVERAL times for retries,
	# thats why we need all sessions related to the last one if its a retry
	$sessions = @($myJobLastSession)
	if ($myJobLastSession.IsRetryMode)
	{
	$sessions = $myJobLastSession.GetOriginalAndRetrySessions($TRUE)
	}

	$myJobLastSessionTasks = $sessions | Get-VBRTaskSession  -ErrorAction SilentlyContinue

	foreach ($myTask in $myJobLastSessionTasks)
	{
		$myTaskName = $myTask.Name -replace "[^ -x7e]" -replace " ","_"

		$myTaskText = "$myTaskText" + "<<<<" + "$myTaskName" + ">>>>" + "`n"

		$myTaskText = "$myTaskText" + "<<<"+ "veeam_client:sep(9)" +">>>" +"`n"

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
    If ($myTask.Progress.StartTime -eq $Null) {
		   $myTaskStartTime = $myTask.Progress.StartTimeLocal
    } Else {
		   $myTaskStartTime = $myTask.Progress.StartTime
    }
    $myTaskStartTime = $myTaskStartTime | Get-Date -Format "dd.MM.yyyy HH\:mm\:ss" -ErrorAction SilentlyContinue

		$myTaskText = "$myTaskText" + "StartTime" + "`t" + "$myTaskStartTime" + "`n"

    # Starting from Version 9.5U3 StopTime is not supported anymore
    If ($myTask.Progress.StopTime -eq $Null) {
    		$myTaskStopTime = $myTask.Progress.StopTimeLocal
    } Else {
    		$myTaskStopTime = $myTask.Progress.StopTime
    }
    $myTaskStopTime = $myTaskStopTime | Get-Date -Format "dd.MM.yyyy HH\:mm\:ss" -ErrorAction SilentlyContinue

		$myTaskText = "$myTaskText" + "StopTime" + "`t" + "$myTaskStopTime" + "`n"

		# Result is a value of type System.TimeStamp. I'm sure there is a more elegant way of formatting the output:
		$myTaskDuration = "" + "{0:D2}" -f $myTask.Progress.duration.Days + ":" + "{0:D2}" -f $myTask.Progress.duration.Hours + ":" + "{0:D2}" -f $myTask.Progress.duration.Minutes + ":" + "{0:D2}" -f $myTask.Progress.duration.Seconds

		$myTaskText = "$myTaskText" + "DurationDDHHMMSS" + "`t" + "$myTaskDuration" + "`n"

		$myTaskAvgSpeed = $myTask.Progress.AvgSpeed

		$myTaskText = "$myTaskText" + "AvgSpeedBps" + "`t" + "$myTaskAvgSpeed" + "`n"

		$myTaskDisplayName = $myTask.Progress.DisplayName

		$myTaskText = "$myTaskText" + "DisplayName" + "`t" + "$myTaskDisplayName" + "`n"

		$myBackupHost = Hostname

		$myTaskText = "$myTaskText" + "BackupServer" + "`t" + "$myBackupHost" + "`n"

		$myTaskText = "$myTaskText" + "<<<<" + ">>>>" +"`n"

	}

    }

write-host $myJobsText
write-host $myTaskText
}

catch
{
$errMsg = $_.Exception.Message
$errItem = $_.Exception.ItemName
Write-Error "Totally unexpected and unhandled error occured:`n Item: $errItem`n Error Message: $errMsg"
Break
}

