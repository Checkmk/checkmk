$CMK_VERSION = "2.0.0p21"
Write-Host "<<<hyperv_vms:sep(9)>>>"

Get-VM | select Name, State, Uptime, Status | ConvertTo-Csv -Delimiter "`t" -NoTypeInformation
