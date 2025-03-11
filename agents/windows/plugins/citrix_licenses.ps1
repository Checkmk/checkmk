# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

<#
.SYNOPSIS
    Retrieves Citrix license usage information from WMI.

.DESCRIPTION
    This script queries the WMI namespace "root\CitrixLicensing" to retrieve
    details about Citrix licenses, including total available and in-use licenses.
    It outputs the data in a tab-separated format.

.PARAMETER None
    This script does not require parameters; it runs on the local system by default.

.OUTPUTS
    Tab-separated values containing:
      - License Name (PLD)
      - Total Licenses Available (Count)
      - Licenses Currently in Use (InUseCount)

.EXAMPLE
    PS> .\citrix_licenses.ps1

    Example output from plugin:
    <<<citrix_licenses>>>
    PVS_STD_CCS     80 0
    PVS_STD_CCS     22 0
    CEHV_ENT_CCS    22 0
    MPS_ENT_CCU     2160 1636
    MPS_ENT_CCU     22 22
    XDT_ENT_UD      22 18
    XDS_ENT_CCS     22 0
    PVSD_STD_CCS    42 0

.NOTES
    Version: 2.5.0b1
    Date: 04.03.2025
    Requires: Citrix Licensing Server installed on the machine.
    If "root\CitrixLicensing" is missing, Citrix Licensing might not be installed.

#>

$CMK_VERSION = "2.5.0b1"

$computer = "."

$licenses = Get-CimInstance -Namespace "root\CitrixLicensing" -query "SELECT * FROM Citrix_GT_License_Pool" -ErrorAction SilentlyContinue

Write-Output "<<<citrix_licenses>>>"

foreach ($license in $licenses) {
    Write-Output "$($license.PLD)`t$($license.Count)`t$($license.InUseCount)"
}
