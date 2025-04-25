# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

<#
.SYNOPSIS
    Script to generate TS Per-Device license usage report.
    Requires Administrator privilege on the license server.
    Works only with WS08 TS License Server, as there is no WMI interface for TS Licensing on earlier versions.
.DESCRIPTION
    The script allows to connect to a remote server or the local machine and retrieve the RDS license information
    using WMI. It expects an optional `-server` argument followed by the server name. If no server name is provided,
    the script will default to querying the local machine.
    The entire argument block is currently not configurable via WATO.
.INPUTS
    .\rds_licenses.ps1 [-server <ServerName>]
.EXAMPLE
    .\rds_licenses.ps1
    This will connect to the local machine and retrieve the RDS license information.
.EXAMPLE
    .\rds_licenses.ps1 -server "RemoteServer"
    This will connect to "RemoteServer" and retrieve the RDS license information.
.NOTES
    Version: 2.5.0b1
    Date: 27.02.2025
#>

$CMK_VERSION = "2.5.0b1"

function Show-Help {
    Write-Host "Usage: GeneratePerDeviceReport.ps1 [-Server ServerName]"
    Write-Host "If no ServerName is provided, then report generation"
    Write-Host "is attempted at the host machine"
    exit 1
}

function Generate-PerDeviceReport {
    param (
        [string]$ServerName = "."
    )
    $NameSpace = "root\cimv2"
    try {
        $ObjWMIService = Get-CimInstance -Namespace $NameSpace -ComputerName $ServerName -ClassName "Win32_TSLicenseKeyPack" -ErrorAction Stop
    } catch {
        Write-Host "Unable to connect to the Namespace" -ForegroundColor Red
        exit 2
    }
    if ($ObjWMIService.Count -eq 0) {
        Write-Host "No license key packs found" -ForegroundColor Red
        exit 5
    }
    Write-Host "<<<rds_licenses:sep(44)>>>"
    Write-Host "KeyPackId,Description,KeyPackType,ProductType,ProductVersion,ProductVersionID,TotalLicenses,IssuedLicenses,AvailableLicenses,ExpirationDate"
    foreach ($ObjectClass in $ObjWMIService) {
        Write-Host "$($ObjectClass.KeyPackId),$($ObjectClass.Description),$($ObjectClass.KeyPackType),$($ObjectClass.ProductType),$($ObjectClass.ProductVersion),$($ObjectClass.ProductVersionID),$($ObjectClass.TotalLicenses),$($ObjectClass.IssuedLicenses),$($ObjectClass.AvailableLicenses),$($ObjectClass.ExpirationDate)"
    }
}

if ($args.Count -gt 2) {
    Show-Help
}
if ($args.Count -eq 1) {
    Show-Help
}
if ($args.Count -eq 2) {
    if ($args[0] -ieq "-server") {
        $ServerName = $args[1]
    } else {
        Show-Help
    }
} else {
    $ServerName = "."
}
Generate-PerDeviceReport -ServerName $ServerName
