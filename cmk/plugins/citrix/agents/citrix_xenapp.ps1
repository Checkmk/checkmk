$CMK_VERSION = "3.0.0b1"
Add-PSSnapin Citrix*

### Citrix XenApp Serverload
$load = Get-XAServerLoad -ServerName $env:computername | Select-Object -ExpandProperty load
"<<<citrix_serverload>>>"
$load

### Citrix XenApp Sessions
$disc = @(Get-XASession -ServerName $env:computername  | where { $_.State -eq "Disconnected" }).count
$activ = @(Get-XASession -ServerName $env:computername  | where { $_.State -eq "Active" }).count
$all = ($disc + $activ)
"<<<citrix_sessions>>>"
"sessions {0}" -f $all
"active_sessions {0}" -f $activ
"inactive_sessions {0}" -f $disc
