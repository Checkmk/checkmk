$computer = "localhost"

### Citrix XenApp Serverload
$loadObject = Get-WmiObject -Namespace 'Root\Citrix' -class 'MetaFrame_Server_LoadLevel' -ComputerName $computer -ErrorAction Stop
"<<<citrix_serverload>>>"
$loadObject.LoadLevel
