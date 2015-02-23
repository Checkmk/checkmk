$computer = "localhost"

### Citrix XenApp Serverload
$loadObject = Get-WmiObject -Namespace 'Root\Citrix' -class 'MetaFrame_Server_LoadLevel' -ComputerName $computer -ErrorAction Stop
"<<<citrix_serverload>>>"
$loadObject.LoadLevel
$computer = "localhost"

### Citrix XenApp Sessions
$serverObject = Get-WmiObject -Namespace root\citrix -Class Metaframe_Server -ComputerName $computer
"<<<citrix_sessions>>>"
"sessions {0}" -f $serverObject.NumberOfSessions
"active_sessions {0}" -f $serverObject.NumberOfActiveSessions
"inactive_sessions {0}" -f $serverObject.NumberOfDisconnectedSessions
