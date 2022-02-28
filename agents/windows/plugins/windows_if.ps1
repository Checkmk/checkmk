$CMK_VERSION = "2.1.0b2"

## runs on windows 2012 or newer
## TeamName        TeamingMode     LoadBalancingAlgorithm  MemberMACAddresses      MemberNames     MemberDescriptions      Speed   GUID
## LAN     Lacp    Dynamic         5C:F3:FC:37:2A:34;5C:F3:FC:37:2A:30     Ethernet;Ethernet 2     QLogic 1/10GbE Server Adapter #2;QLogic 1/10GbE Server Adapter  10000000000;10000000000 {11477AB1-0A749C-8768-A17F47C02A1F};{2B232067-0EE5-41EE-B498-0CA2FE8715D0}
if ((([Environment]::OSVersion.Version.Major -eq "6") -and ([Environment]::OSVersion.Version.Minor -ge "2")) -or ([Environment]::OSVersion.Version.Major -ge "7")){
	Write-Host "<<<winperf_if_teaming:sep(9)>>>"
	$teams = Get-NetLbfoTeam
	if ($teams){
		Write-Host "TeamName`tTeamingMode`tLoadBalancingAlgorithm`tMemberMACAddresses`tMemberNames`tMemberDescriptions`tSpeed`tGUID"
		foreach ($team in $teams){
			$membermacs = $null
			$members = $null
			$netinterface = $null
			$netspeed = $null
			$netguid = $null
			Write-Host -NoNewline $team.Name`t
			Write-Host -NoNewline $team.tm`t
			Write-Host -NoNewline $team.lba`t
			foreach ($slave in $team.members){
				$membermacs += (Get-Netadapter $slave).MacAddress + ";"
				$members += $slave + ";"
				$netinterface += (Get-Netadapter $slave).InterfaceDescription + ";"
				$netspeed += [String](Get-Netadapter $slave).Speed + ";"
				$netguid += (Get-Netadapter $slave).InterfaceGuid + ";"
			}
			$membermacs = $membermacs.Replace("-",":")
			$membermacs = $membermacs.TrimEnd(";") + "`t"
			Write-Host -NoNewline  $membermacs
			$members = $members.TrimEnd(";") + "`t"
			Write-Host -NoNewline $members
			$netinterface = $netinterface.TrimEnd(";") + "`t"
			Write-Host -NoNewline $netinterface
			$netspeed = $netspeed.TrimEnd(";") + "`t"
			Write-Host -NoNewline $netspeed
			$netguid = $netguid.TrimEnd(";")
			Write-Host $netguid
		}
	}
}

# runs on windows 2003 or newer
if ([Environment]::OSVersion.Version.Major -ge "5"){
	try {
		Write-Host "<<<winperf_if_get_netadapter:sep(124)>>>"
		foreach ($net in Get-NetAdapter -IncludeHidden){
			Write-Host ("$($net.InterfaceDescription)|" +
			            "$($net.InterfaceAlias)|" +
			            "$($net.Speed)|" +
			            "$($net.InterfaceOperationalStatus)|" +
			            "$($net.Status)|" +
			            "$($net.MACAddress)|" +
			            "$($net.InterfaceGuid)")
		}
	}
	catch [System.Management.Automation.CommandNotFoundException] {
		Write-Host "<<<winperf_if_win32_networkadapter:sep(9)>>>"
		Write-Host "Node`tMACAddress`tName`tNetConnectionID`tNetConnectionStatus`tSpeed`tGUID"
		foreach ($net in Get-WmiObject Win32_NetworkAdapter)
		{
			if ($net.netconnectionid){
				Write-Host      $env:COMPUTERNAME "`t"`
						$net.macaddress "`t"`
						$net.name "`t"`
						$net.netconnectionid "`t"`
						$net.netconnectionstatus "`t"`
						$net.speed "`t"`
						$net.GUID
			}
		}
	}
}


