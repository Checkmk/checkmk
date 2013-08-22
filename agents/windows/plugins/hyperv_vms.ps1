Write-Host –NoNewLine "<<<hyperv_vms>>>"
Get-VM | format-table -HideTableHeaders -property Name, State, Uptime, Status
