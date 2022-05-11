$CMK_VERSION = "2.0.0p25"
# check_datacore.ps1
# Version 0.2
# Author : Andre Eckstein, Andre.Eckstein@Bechtle.com
# Prerequisites
# -------------
# 1. Datacore SANsymphony V8 or V9 must be installed
# SANmelody and Sansymphony are not supported.
#
# 2. The SANsymphony CMDlets need to be installed on the monitored Datacore Server
# If not installed you need to install the CMDlets with the SANsymphony V installation routine.
# - Enabling of .net 4 Framwork support in PowerShell
# Support for .net 4 must be enabled. To achieve this, create a file with the name powershell.exe.config with the following content:
#
# <?xml version="1.0" encoding="utf-8" ?>
# <configuration>
#   <startup useLegacyV2RuntimeActivationPolicy="true">
#         <supportedRuntime version="v4.0"/>
#         <supportedRuntime version="v2.0.50727" />
#     </startup>
# </configuration>
#
# And just put that file into the following directories:
# c:\windows\system32\WindowsPowerShell\v1.0\ and c:\windows\sysWOW64\WindowsPowerShell\v1.0\
#
# 3. A working Checkmk agent on the monitored host
# Be sure that the Checkmk agent is working without the sansymphony.ps1 plugin. You can verify this by calling telnet <servername or ip> 6556.
# There should be a lot text output showing the different sections.

#configuration:

$ssvusername="Username"
$ssvpassword="Password"
$ssvhostname="Hostname"

# import Datacore cmdlets (maybe we should do this persistently to speed up the check runtime

Import-Module "C:\Program Files\DataCore\SANsymphony\DataCore.Executive.Cmdlets.dll" -DisableNameChecking -ErrorAction Stop;

#set up PowerShell connection to local server

Connect-DcsServer -Server $ssvhostname -UserName $ssvusername -Password $ssvpassword -Connection check_mk | Out-Null

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



	# Output state of all Volumes

	write-host "<<<sansymphony_virtualdiskstatus>>>"
	foreach ($Item in $volumes) {
	$virtualdiskalias=$Item.Alias -replace '\s+', '_'
	write-host $virtualdiskalias $Item.DiskStatus
	}

	# Output amount of unacknowlegded alerts

	write-host "<<<sansymphony_alerts>>>"
	$amountofalerts=$ssvalerts.length
	write-host $amountofalerts

	# Output type and status of ports

	write-host "<<<sansymphony_ports>>>"
	foreach ($Item in $dcsports) {
	if ($Item.Alias -ne "Loopback Port")
		{
		$portalias=$Item.Alias -replace '\s+', '_'
		write-host $portalias $Item.PortType $Item.Connected
		}
	}

	# output server and cachestate information

	write-host "<<<sansymphony_serverstatus>>>"
	foreach ($Item in $serverinfo) {
		write-host $Item.State $Item.Cachestate
		}

	# output allocation of disk pools

	write-host "<<<sansymphony_pool>>>"

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

        $c = @()
        $d = @()
        $e = @()
	foreach ($Item in $poolstatus) {
            $c += $Item.PoolStatus
            $d += $Item.PoolMode
            $e += $Item.Type
	}

	$i=0
	do {
            Write-Host $a[$i] $b[$i] $c[$i] $d[$i] $e[$i]; $i++
           }while ($i -le $poolinfo.length-1)

	exit 0

	}

else
	{
   	exit 2
	}

