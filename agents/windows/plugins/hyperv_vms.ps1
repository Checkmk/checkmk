Write-Host -NoNewLine "<<<hyperv_vms>>>"
Get-VM | format-table -HideTableHeaders -Autosize -property Name, State, Uptime, Status
Write-Host
