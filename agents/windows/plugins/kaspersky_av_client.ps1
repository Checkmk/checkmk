# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

<#
.SYNOPSIS
Check_MK windows agent plugin to gather information about fullscan age and
signature date and connection date to Kaspersky Management Server of
Kaspersky Anti-Virus Client.
All registry keys have values in the UTC time, format: dd-MM-yyyy HH-mm-ss
.DESCRIPTION
This script:
1) reads the relevant registry keys
2) converts the Kaspersky date/time string (in the format dd-MM-yyyy HH-mm-ss) to a DateTime object
3) adjusts the date based on the local time zone
4) converts the date to the checkmk (server-side) format: dd.MM.yyyy HH:mm:ss.
Regardless of the system's date/time settings
.EXAMPLE
# Run the script to gather Kaspersky Anti-Virus Client information
.\kaspersky_av_client.ps1
#>

$CMK_VERSION = "2.5.0b1"
$strStatisticsLoc = "HKLM:\SOFTWARE\Wow6432Node\KasperskyLab\Components\34\1103\1.0.0.0\Statistics\AVState"

function StrDateTimeToCheckmkFormat {
    param (
        [string]$strDateTime
    )

    $dateTime = [datetime]::ParseExact($strDateTime, "dd-MM-yyyy HH-mm-ss", $null)
    $localDateTimeString = $dateTime.ToLocalTime().ToString("dd.MM.yyyy HH:mm:ss")
    Write-Output $localDateTimeString
}

$strProtection_LastConnected = Get-ItemPropertyValue $strStatisticsLoc -Name Protection_LastConnected

# If the strProtection_LastConnected key can be read Kaspersky AV is assumed to be installed
if ($null -ne $strProtection_LastConnected) {
    Write-Output "<<<kaspersky_av_client>>>"

    # Protection_BasesDate key is set with old signatures from installer
    $strProtection_BasesDate = Get-ItemPropertyValue $strStatisticsLoc -Name Protection_BasesDate
    if (-not $strProtection_BasesDate) {
        Write-Output "Signatures Missing"
    }
    else {
        Write-Output "Signatures $(StrDateTimeToCheckmkFormat $strProtection_BasesDate)"
    }

    # Protection_LastFscan key deployed empty on installation
    $strProtection_LastFscan = Get-ItemPropertyValue $strStatisticsLoc -Name Protection_LastFscan
    if (-not $strProtection_LastFscan) {
        Write-Output "Fullscan Missing"
    }
    else {
        Write-Output "Fullscan $(StrDateTimeToCheckmkFormat $strProtection_LastFscan)"
    }
}
else {
    # Write-Output "<<<kaspersky_av_client>>>"
    # Write-Output "Signatures Missing"
    # Write-Output "Fullscan Missing"
    # Write-Output "Missing Kaspersky Client"
}
