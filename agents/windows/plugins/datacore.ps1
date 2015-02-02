# check_datacore.ps1
# Version 0.2
# Author : Andre Eckstein, Andre.Eckstein@Bechtle.com

#configuration:

$ssvusername="Username"
$ssvpassword="Password"
$ssvhostname="Hostname"

# import Datacore cmdlets (maybe we should do this persistently to speed up the check runtime 

Import-Module "C:\Program Files\DataCore\SANsymphony\DataCore.Executive.Cmdlets.dll" -DisableNameChecking -ErrorAction Stop;

#set up PowerShell connection to local server

Connect-DcsServer -Server $ssvhostname -UserName $ssvusername -Password $ssvpassword -Connection check_mk

# if the connection was succesfull, we´ll go on

if($?)  {
	# Gather all the information we need

	$volumes=@(Get-DcsVirtualDisk -Server $ssvhostname)
	$poolstatus=@(Get-DcsPool -Server $ssvhostname)
	$poolinfo=@(Get-DcsPool -Server $ssvhostname| Get-DcsPerformanceCounter)
	$ssvalerts=@(Get-DcsAlert)
	$serverinfo=@(get-dcsserver -server $ssvhostname)
	$dcsports=@(get-dcsport -Machine $ssvhostname)

	# Now disconnect, we´ve got everything we need

	Disconnect-DcsServer -Connection check_mk

	# Output state of all Disk Pools

	write-host "<<<datacore_poolstatus>>>"
	foreach ($Item in $poolstatus) {
	$poolalias=$Item.Alias -replace '\s+', '_'
	write-host $poolalias $Item.PoolStatus $Item.PoolMode $Item.Type
	}

	# Output state of all Volumes

	write-host "<<<datacore_virtualdiskstatus>>>"
	foreach ($Item in $volumes) {
	$virtualdiskalias=$Item.Alias -replace '\s+', '_'
	write-host $virtualdiskalias $Item.DiskStatus
	}

	# Output amount of unacknowlegded alerts

	write-host "<<<datacore_alerts>>>"
	$amountofalerts=$ssvalerts.length
	write-host $amountofalerts

	# Output type and status of ports

	write-host "<<<datacore_ports>>>"
	foreach ($Item in $dcsports) {
	if ($Item.Alias -ne "Loopback Port")
		{	
		$portalias=$Item.Alias -replace '\s+', '_'
		write-host $portalias $Item.PortType $Item.Connected
		}
	}

	# output server and cachestate information

	write-host "<<<datacore_serverstatus>>>"
	foreach ($Item in $serverinfo) {
		write-host $Item.State $Item.Cachestate
		}

	# output allocation of disk pools

	write-host "<<<datacore_poolallocation>>>"
	
	$a = @()
	foreach ($Item in $poolstatus) {
	$poolalias=$Item.Alias -replace '\s+', '_'
	$a += $poolalias
	}
	
	$b = @()
	foreach ($Item in $poolinfo) {
	$poolallocation=$Item.PercentAllocated
	$b += $poolallocation
	}

	$i=0
	do 
	{Write-Host $a[$i] $b[$i]; $i++}
	while ($i -le $poolinfo.length-1)

	exit 0

	}

else
	{
   	exit 2
	}

