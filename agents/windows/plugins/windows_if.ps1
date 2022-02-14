$CMK_VERSION = "2.0.0p21"
## Windows Teaming Interfaces
## runs on windows 2003 or newer
if ([Environment]::OSVersion.Version.Major -ge "5"){
	Write-Host "<<<winperf_if:sep(9)>>>"
}

## runs on windows 2012 or newer
## [teaming_start]
## TeamName        TeamingMode     LoadBalancingAlgorithm  MemberMACAddresses      MemberNames     MemberDescriptions      Speed   GUID
## LAN     Lacp    Dynamic         5C:F3:FC:37:2A:34;5C:F3:FC:37:2A:30     Ethernet;Ethernet 2     QLogic 1/10GbE Server Adapter #2;QLogic 1/10GbE Server Adapter  10000000000;10000000000 {11477AB1-0A749C-8768-A17F47C02A1F};{2B232067-0EE5-41EE-B498-0CA2FE8715D0}
## [teaming_end]
if ((([Environment]::OSVersion.Version.Major -eq "6") -and ([Environment]::OSVersion.Version.Minor -ge "2")) -or ([Environment]::OSVersion.Version.Major -ge "7")){
	$teams = Get-NetLbfoTeam
	if ($teams){
		Write-Host "[teaming_start]"
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
		Write-Host "[teaming_end]"
	}
}

# runs on windows 2003 or newer
# Node    MACAddress      Name    NetConnectionID NetConnectionStatus     Speed   GUID
# NODE01   42:F2:E9:21:BE:D1       IBM USB Remote NDIS Network Device #2   Local Area Connection 2         2       9728000         {A447D54F-0E4B-40B3-9FBA-228F7DCE8FC7}
# NODE01   40:F2:E9:21:BE:D2       Intel(R) I350 Gigabit Network Connection        Ethernet 3      7       9223372036854775807     {1C656D16-F30D-4714-9A7E-B3D3F9AD52FA}
# NODE01   40:F2:E9:21:BE:D3       Intel(R) I350 Gigabit Network Connection #2     Ethernet 4      7       9223372036854775807     {F9C89525-0500-4A6B-95AC-95F66BDA739A}
# NODE01   40:F2:E9:21:BE:D4       Intel(R) I350 Gigabit Network Connection #3     Ethernet 5      7       9223372036854775807     {A0D28181-6DF8-4A80-9837-D2933D013510}
# NODE01   40:F2:E9:21:BE:D5       Intel(R) I350 Gigabit Network Connection #4     Ethernet 6      7       9223372036854775807     {95CA2691-7AFA-4842-A769-F521FE6173B2}
# NODE01   5C:F3:FC:37:2A:30       QLogic 1/10GbE Server Adapter   Ethernet 2      2               {2B232067-0EE5-41EE-B498-0CA2FE8715D0}
# NODE01   5C:F3:FC:37:2A:34       QLogic 1/10GbE Server Adapter   Ethernet        2               {11477AB1-0A73-449C-8768-A17F47C02A1F}
# NODE01   5C:F3:FC:37:2A:30       Microsoft Network Adapter Multiplexor Driver    LAN     2       20000000000     {4FCE4C48-6217-465A-B807-B61499AE570C}
if ([Environment]::OSVersion.Version.Major -ge "5"){
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


