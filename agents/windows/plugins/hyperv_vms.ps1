$CMK_VERSION = "2.1.0b2"
Write-Host "<<<hyperv_vms:sep(9)>>>"

Get-VM | select Name, State, Uptime, Status | ConvertTo-Csv -Delimiter "`t" -NoTypeInformation
