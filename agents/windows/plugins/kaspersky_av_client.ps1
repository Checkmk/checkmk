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
$g_AVStateRegKey = "HKLM:\SOFTWARE\Wow6432Node\KasperskyLab\Components\34\1103\1.0.0.0\Statistics\AVState"

function StrDateTimeToCheckmkFormat {
    param (
        [string]$strDateTime
    )
    try {
        $dateTime = [datetime]::ParseExact($strDateTime, "dd-MM-yyyy HH-mm-ss", $null)
        $localDateTimeString = $dateTime.ToLocalTime().ToString("dd.MM.yyyy HH:mm:ss")
    }
    catch {
        Write-Output "Error parsing date: $($_.Exception.Message)"
        return
    }

    Write-Output $localDateTimeString
}

function GetKasperskyRegistryDateValue {
    param (
        [string]$RegistryPath,
        [string]$Name
    )
    $value = Get-ItemPropertyValue $RegistryPath -Name $Name
    if ($null -eq $value -or $value -eq "") { return $null }
    return $value
}

function GetKasperskyFullscanStatus {
    $lastFscan = GetKasperskyRegistryDateValue $g_AVStateRegKey "Protection_LastFscan"
    if (-not $lastFscan) {
        return "Fullscan Missing"
    }
    return "Fullscan $(StrDateTimeToCheckmkFormat $lastFscan)"
}

function GetKasperskySignatureStatus {
    $basesDate = GetKasperskyRegistryDateValue $g_AVStateRegKey "Protection_BasesDate"
    if (-not $basesDate) {
        return "Signatures Missing"
    }
    return "Signatures $(StrDateTimeToCheckmkFormat $basesDate)"
}

function GetKasperskyAvClientStatus {
    $lastConnected = GetKasperskyRegistryDateValue $g_AVStateRegKey "Protection_LastConnected"
    if ($null -ne $lastConnected) {
        Write-Output "<<<kaspersky_av_client>>>"
        try {
            Write-Output (GetKasperskySignatureStatus)
        }
        catch {
            Write-Output "GetKasperskySignatureStatus Error: $($_.Exception.Message)"
        }
        try {
            Write-Output (GetKasperskyFullscanStatus)
        }
        catch {
            Write-Output "GetKasperskyFullscanStatus Error: $($_.Exception.Message)"
        }
    }
    else {
        # Write-Output "<<<kaspersky_av_client>>>"
        # Write-Output "Signatures Missing"
        # Write-Output "Fullscan Missing"
        # Write-Output "Missing Kaspersky Client"
    }
}

GetKasperskyAvClientStatus
