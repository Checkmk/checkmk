$CMK_VERSION = "2.4.0b7"
Write-Host "<<<hyperv_vms:sep(9)>>>"

Hyper-V\Get-VM | select Name, State, Uptime, Status | ConvertTo-Csv -Delimiter "`t" -NoTypeInformation
