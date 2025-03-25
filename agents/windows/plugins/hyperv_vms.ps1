$CMK_VERSION = "2.5.0b1"
Write-Host "<<<hyperv_vms:sep(9)>>>"

Hyper-V\Get-VM | select Name, State, Uptime, Status | ConvertTo-Csv -Delimiter "`t" -NoTypeInformation
