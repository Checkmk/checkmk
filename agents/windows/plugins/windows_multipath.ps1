$CMK_VERSION = "2.5.0b1"

# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# MPIO_PATH_INFORMATION WMI Class
# A WMI client uses this class to query the MPIO driver for information
# regarding all paths that are associated with an MPIO disk.
# https://learn.microsoft.com/en-us/windows-hardware/drivers/storage/mpio-path-information-wmi-class
# Author: Diana Ivanchevska
# Date: 2025-02-10

$computerName = "."

# Added for check_mk parsing
Write-Host "<<<windows_multipath>>>"

# WMI connection to Root WMId
# Starting in PowerShell 3.0, Get-WmiObject cmdlet has been superseded by Get-CimInstance.
$mpioPaths = Get-CimInstance -Namespace "Root\WMI" -ClassName "MPIO_PATH_INFORMATION" -ComputerName $computerName

foreach ($path in $mpioPaths) {
  Write-Host $path.NumberPaths
}
