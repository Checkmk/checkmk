$CMK_VERSION = "2.1.0b7"
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This Check_Mk Plugin checks a Citrix XenDesktop / XenApp 7.x Farm

# Contributed by Meik Vogel

# Prerequisites : Script must run on a XenDesktop Controller as Citrix Admin

# Please configure these parameters according to your setup

# Define the maximum of counted machines (default is only 250)
$maxmachines = "500"

# Define the maximum of counted users (default is only 250)
$maxusers = "2000"

# Define the name of the DNS Domain
$DNSdomain = ".subdomain.domain"

if ((Get-PSSnapin "Citrix.Common.Commands" -EA silentlycontinue) -eq $null) {
	try { Add-PSSnapin Citrix.* -ErrorAction Stop }
	catch { write-error "Error Citrix.* Powershell snapin"; Return }
}

$XASessions = Get-BrokerSession -Property HostedMachineName,Sessionstate -MaxrecordCount $maxusers | Group-Object HostedMachineName, Sessionstate | Sort-Object Name | select-object Name,Count
$XAmachines = Get-BrokerMachine  -MaxRecordCount $maxmachines
$Controllers = Get-BrokerController

foreach ($Controller in $Controllers) {
	# Column Name of Controller
	$ControllerDNS = $Controller | %{ $_.DNSName }
	$ControllerDNS = $ControllerDNS.Replace($DNSdomain,$null)
	"<<<<$ControllerDNS>>>>"
	"<<<citrix_controller>>>"
	# Column ControllerState / Gets only Controllers currently in the specified state. Valid values are: Failed, Off, On, and Active.
	$ControllerState = $Controller | %{ $_.State }
	"ControllerState $ControllerState"

	# Column ControllerVersion / Gets only Controllers running the specified version of the broker service.
	$ControllerVersion = $Controller | %{ $_.ControllerVersion }
	"ControllerVersion $ControllerVersion"

	# Column DesktopsRegistered / Gets only Controllers that have the specified number of desktops currently registered.
	$ControllerDesktopsRegistered = $Controller | %{ $_.DesktopsRegistered }
	"DesktopsRegistered $ControllerDesktopsRegistered"

	# Column LicensingServerState / Gets only Controllers in the specified licensing server state. Valid values are: ServerNotSpecified, NotConnected, OK, LicenseNotInstalled, LicenseExpired, Incompatible and Failed.
	$LicensingServerState = $Controller |  %{ $_.LicensingServerState }
	"LicensingServerState $LicensingServerState"

	# Column LicensingGraceState / Gets only Controllers in the specified licensing grace state. Valid values are: NotActive, InOutOfBoxGracePeriod, InSupplementalGracePeriod, InEmergencyGracePeriod and GracePeriodExpired.
	$LicensingGraceState = $Controller |  %{ $_.LicensingGraceState }
	"LicensingGraceState $LicensingGraceState"

	# Column ActiveSiteServices / The Broker site services active on the controller.
	$ActiveSiteServices = $Controller |  %{ $_.ActiveSiteServices }
	"ActiveSiteServices $ActiveSiteServices"

	# TotalFarmActiveSessions / Gets the total Farm User Sessions
	$totalactive_sessions = $XASessions | Where-Object {$_.Name -like "*Active*"} | %{ $_.Count }
	if (!$totalactive_sessions) {$totalactive_sessions = 0}
	$totalactive_sessions = $totalactive_sessions | Measure-Object -Sum | %{ $_.Sum }
	"TotalFarmActiveSessions $totalactive_sessions"

	# TotalFarmInactiveSessions / Gets the total Farm User Inactive Sessions
	$totalinactive_sessions = $XASessions | Where-Object {$_.Name -like "*Disconnected*"} | %{ $_.Count }
	if (!$totalinactive_sessions) {$totalinactive_sessions = 0}
	$totalinactive_sessions = $totalinactive_sessions | Measure-Object -Sum | %{ $_.Sum }
	"TotalFarmInactiveSessions $totalinactive_sessions"
	"<<<<>>>>"
}

	foreach ($XAmachine in $XAmachines) {

		# Column Name of Machine / Gets machines with the specific machine name known to the hypervisor.
		$HostedMachineName = $XAmachine | %{ $_.HostedMachineName }
		if([string]::IsNullOrEmpty($HostedMachineName)) {
			continue;
		}
		"<<<<$HostedMachineName>>>>"
		"<<<citrix_state>>>"
		# Column CatalogNameName / Gets machines from the catalog with the specific name.
		$CatalogName = $XAmachine | %{ $_.CatalogName }
		"Catalog $CatalogName"

		# Column Controller / Gets machines with a specific DNS name of the controller they are registered with.
		$Controller = $XAmachine | %{ $_.ControllerDNSName }
		"Controller $Controller"

		# Column DesktopGroupName / Gets machines from a desktop group with the specified name.
		$DesktopGroupName = $XAmachine | %{ $_.DesktopGroupName }
		"DesktopGroupName $DesktopGroupName"

		# Column FaultState / Gets machines currently in the specified fault state.
		$FaultState = $XAmachine | %{ $_.FaultState }
		"FaultState $FaultState"

		# Column HostingServerName / Gets machines by the name of the hosting hypervisor server.
		$HostingServerName = $XAmachine | %{ $_.HostingServerName }
		"HostingServer $HostingServerName"

		# Column MaintenanceMode / Gets machines by whether they are in maintenance mode or not.
		$MaintenanceMode = $XAmachine  | %{ $_.InMaintenanceMode }
		"MaintenanceMode $MaintenanceMode"

		# Column PowerState / Gets machines with a specific power state. Valid values are Unmanaged, Unknown, Unavailable, Off, On, Suspended, TurningOn, TurningOff, Suspending, and Resuming.
		$PowerState = $XAmachine  | %{ $_.PowerState }
		"PowerState $PowerState"

		# Column RegistrationState / Gets machines in a specific registration state. Valid values are Unregistered, Initializing, Registered, and AgentError.
		$RegistrationState = $XAmachine  | %{ $_.RegistrationState }
		"RegistrationState $RegistrationState"

		# Column VMToolsState / Gets machines with a specific VM tools state. Valid values are NotPresent, Unknown, NotStarted, and Running.
		$VMToolsState  = $XAmachine | %{ $_.VMToolsState }
		"VMToolsState $VMToolsState"

		# Column AgentVersion / Gets machines with a specific Citrix Virtual Delivery Agent version.
		$AgentVersion  = $XAmachine | %{ $_.AgentVersion }
		"AgentVersion $AgentVersion"

		# Column Serverload / Gets machines by their current load index.
		$Serverload = $XAmachine  | %{ $_.LoadIndex }
		if(-NOT ([string]::IsNullOrEmpty($Serverload))) {
		    "<<<citrix_serverload>>>"
		    "$Serverload"
		}

		# Column SessionCount / Count of number of active / inactive sessions on the machine.
		$Sessions = $XAmachine | %{ $_.SessionCount }
		"<<<citrix_sessions>>>"
		if ($XASessions -match $HostedMachineName) {
		"sessions $Sessions"
			$active_sessions = $XASessions | Where-Object {$_.Name -like "$HostedMachineName, Active"} | %{ $_.Count }
			if (!$active_sessions) {$active_sessions = 0}
		"active_sessions $active_sessions"
			$inactive_sessions = $XASessions | Where-Object {$_.Name -like "$HostedMachineName, Disconnected"} | %{ $_.Count }
			if (!$inactive_sessions) {$inactive_sessions = 0}
		"inactive_sessions $inactive_sessions"

		}
		else {
		"sessions $Sessions"
		"active_sessions 0"
		"inactive_sessions 0"

		}
		 "<<<<>>>>"
		if ($HostingServerName) {
            $HostingServerName = $HostingServerName.Replace($DNSdomain,$null)

		    "<<<<$HostingServerName>>>>"
            "<<<citrix_hostsystem>>>"
		    "VMName $HostedMachineName"

		    # Column HypervisorConnectionName / Gets machines with a specific Citrix Virtual Delivery Agent version.
		    $HypervisorConnectionName  = $XAmachine | %{ $_.HypervisorConnectionName }
		    "CitrixPoolName $HypervisorConnectionName"
		    "<<<<>>>>"
        }
	}
"<<<<>>>>"
