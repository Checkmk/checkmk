# 
# Get Windows tasks for check_mk
# 
# Changelog: 	v0.02	German servers will now write their output in English
#				v0.03	Fixed a bug with German language output
#

Write-Host "<<<windows_tasks:sep(58)>>>"
$lang = Get-UICulture | select -expand LCID
if ($lang -eq 1031){
	$tasks = schtasks /query /fo csv -v | ConvertFrom-Csv
	foreach ($task in $tasks){
		if (($task.HostName -match "^$($Env:Computername)$") -and ($task.AufgabenName -notlike '\Microsoft*') -and ($task.AufgabenName -notlike '*zachteHRM*')){
			Write-Host "TaskName `t: "$task.AufgabenName
			Write-Host "Last Run Time `t: "$task.'Letzte Laufzeit'
			Write-Host "Next Run Time `t: "$task.'Nächste Laufzeit'
			Write-Host "Last Result `t: "$task.'Letztes Ergebnis'
			if ($task.'Status der geplanten Aufgabe' -eq 'Aktiviert'){
				Write-Host "Scheduled Task State `t: Enabled"
			} else {
				Write-Host "Scheduled Task State `t: "$task.'Status der geplanten Aufgabe'
			}
			Write-Host ""
		}
	}
} elseif ($lang -eq 1033){
	schtasks /query /fo csv -v | ConvertFrom-Csv | ? {$_.HostName -match "^$($Env:Computername)$" -and $_.TaskName -notlike '\Microsoft*' -and $_.TaskName -notlike '*zachteHRM*'} | fl taskname,"last run time","next run time","last result","scheduled task state"
}