# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

<#
.SYNOPSIS
Checks for pending Windows updates and logs relevant information.
.DESCRIPTION
Queries Windows Update for updates that are not installed and not hidden.
Determines if a system reboot is required.
Outputs the number and names of important and optional updates.
.LINK
https://learn.microsoft.com/en-us/windows/win32/api/wuapi/nf-wuapi-iupdatesearcher-search
.NOTES
Uses COM objects to interact with Windows Update.
Requires administrative privileges to run.

Date: 2025-02-19
Version: 2.5.0b1
#>

$CMK_VERSION = "2.5.0b1"

# Output UTF-16 BOM
[Console]::OutputEncoding = [System.Text.Encoding]::Unicode
Write-Output ([char]0xFEFF)

function ReadFromRegistry {
    param (
        [string]$RegistryKey,
        [string]$Default
    )
    try {
        Write-Verbose "Reading registry key: $RegistryKey"
        $value = Get-ItemProperty -Path $RegistryKey -ErrorAction Stop | Select-Object -ExpandProperty "(default)"
        Write-Verbose "Registry key found: $value"
        return $value
    } catch {
        Write-Verbose "Failed to read registry key: $RegistryKey. Using default value: $Default"
        return $Default
    }
}

function ProcessSearchResult {
    param (
        $SearchResult,
        $RebootRequired,
        $RebootTime
    )

    if ($SearchResult.ResultCode -ne 2) {
        Write-Output "<<<windows_updates>>>"
        Write-Output "x x x"
        Write-Output "There was an error getting update information. Maybe Windows Update is not activated."
        return
    }

    Write-Verbose "Found $($SearchResult.Updates.Count) pending updates."
    Write-Verbose "Processing update results..."
    $ImportantUpdates = @()
    $OptionalUpdates = @()
    $NumImp = 0
    $NumOpt = 0
    foreach ($Update in $SearchResult.Updates) {
        if ($Update.AutoSelectOnWebSites) {
            $ImportantUpdates += $Update.Title
            $NumImp++
        } else {
            $OptionalUpdates += $Update.Title
            $NumOpt++
        }
    }

    Write-Output "<<<windows_updates>>>"
    Write-Output "$RebootRequired $NumImp $NumOpt"
    Write-Output ($ImportantUpdates -join "; ")
    Write-Output ($OptionalUpdates -join "; ")
    Write-Output $RebootTime
}

Write-Verbose "Starting windows update check..."

$RegPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update"
Write-Verbose "Defined registry path for Windows Update: $RegPath"
$RebootTime = ReadFromRegistry -RegistryKey "$RegPath\NextFeaturedUpdatesNotificationTime" -Default "no_key"

Write-Verbose "Checking for pending updates..."
$RebootRequired = (New-Object -ComObject Microsoft.Update.SystemInfo).RebootRequired
$UpdateSession = New-Object -ComObject Microsoft.Update.Session
$UpdateSearcher = $UpdateSession.CreateUpdateSearcher()
$SearchResult = $UpdateSearcher.Search("IsInstalled = 0 and IsHidden = 0")

# Handle search errors
# Possible result codes
# NotStarted = 0,
# InProgress = 1,
# Succeeded = 2,
# SucceededWithErrors = 3,
# Failed = 4,
# Aborted = 5

Write-Verbose "Search is finished with result code:  $($SearchResult.ResultCode)"
ProcessSearchResult -SearchResult $SearchResult -RebootRequired $RebootRequired -RebootTime $RebootTime
