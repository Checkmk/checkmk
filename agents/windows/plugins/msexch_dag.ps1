$CMK_VERSION = "2.1.0b1"
## MSExchange Replication
## Load Exchange Management Powershell Plugin
try{ (Add-PSSnapin Microsoft.Exchange.Management.PowerShell.E2010 -ErrorAction:Stop) }

## exit without any output if this fails
catch{exit}

write-host "<<<msexch_dag:sep(58)>>>"
Get-MailboxDatabaseCopyStatus | Format-List

write-host "<<<msexch_replhealth:sep(58)>>>"
Test-ReplicationHealth | Format-List
