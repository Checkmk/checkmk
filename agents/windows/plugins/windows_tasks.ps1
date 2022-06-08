$CMK_VERSION = "2.1.0p3"
####
## Monitor Windows Tasks
##

Write-Host "<<<windows_tasks:sep(58):encoding(cp437)>>>"
$lang = Get-UICulture | select -expand LCID

## "..",".\n..","aaa"\n
## We assume that correct newline can be placed only after "
## Processing
## \r\n   -> 'Z_Z'
## "      -> 'o_o'
## o_oZ_Z -> '\"\r\n' # the only valid new line symbols
## o_o    -> '"'
## Z_Z    -> ''

## encoding "\n and "
$raw = (schtasks /query /fo csv -v | out-string) -replace '\r\n', 'Z_Z'
$l = $raw -replace '\"', 'o_o'
## decoding
$d = $l -replace 'o_oZ_Z', "`"`r`n"
$d = $d -replace 'o_o', '"'
$d = $d -replace 'Z_Z', ''
$tasks = $d | ConvertFrom-Csv

if ($lang -eq 1031){
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
} elseif ($lang -eq 1033 -or $lang -eq 2057){
	$tasks | ? {$_.HostName -match "^$($Env:Computername)$" -and $_.TaskName -notlike '\Microsoft*' -and $_.TaskName -notlike '*zachteHRM*'} | fl taskname,"last run time","next run time","last result","scheduled task state" | out-string -width 4096
}
