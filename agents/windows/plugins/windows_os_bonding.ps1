# Changelog: 	v0.02	Rearranged info
#				v0.03	Included try block for older operating systems
#				v0.04	Added speed info
#

try {
	$teams = Get-NetLbfoTeam
} catch {}
if ($teams){
	Write-Host "<<<windows_os_bonding:sep(58)>>>"
	foreach ($team in $teams){
		Write-Host Team Name: $team.Name
		Write-Host Bonding Mode: $team.LoadBalancingAlgorithm
		Write-Host Status: $team.Status
		$bondspeed = (Get-NetAdapter | where {$_.InterfaceDescription -match "Multiplex"}).LinkSpeed
		Write-Host Speed: $bondspeed `n
		foreach ($slave in $team.members){
			Write-Host Slave Name: $slave
			$net = Get-Netadapter $slave
			Write-Host Slave Interface: $net.ifName
			Write-Host Slave Description: $net.interfaceDescription
			Write-Host Slave Status: $net.Status
			Write-Host Slave Speed: $net.LinkSpeed
			Write-Host Slave MAC address: $net.MacAddress `n
		}
	}
}

