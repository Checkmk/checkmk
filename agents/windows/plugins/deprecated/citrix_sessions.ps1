$computer = "localhost"

### Citrix XenApp Sessions
$serverObject = Get-WmiObject -Namespace root\citrix -Class Metaframe_Server -ComputerName $computer
"<<<citrix_sessions>>>"
"sessions {0}" -f $serverObject.NumberOfSessions
"active_sessions {0}" -f $serverObject.NumberOfActiveSessions
"inactive_sessions {0}" -f $serverObject.NumberOfDisconnectedSessions
