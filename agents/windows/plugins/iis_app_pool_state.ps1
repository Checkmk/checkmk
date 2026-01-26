$CMK_VERSION = "2.4.0p21"
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Reference:
# https://powershellmagazine.com/2013/07/19/querying-performance-counters-from-powershell/
# https://learn.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhlookupperfnamebyindexa
Function Get-LocalizedEnglishPerfCounterName {
    param
    (
        [Parameter(Mandatory = $true)]
        [string] $Name
    )

    $enMappingRegistryKey = 'Registry::HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Perflib\009'
    $enMapping = (Get-ItemProperty -Path $enMappingRegistryKey -Name Counter).Counter.tolower()
    $index = $enMapping.IndexOf($name.tolower())
    if ($index -eq -1) {
        return $null
    }
    $counterId = $enMapping[$index - 1]

    $localMappingRegistryKey = 'Registry::HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Perflib\CurrentLanguage'
    $localMapping = (Get-ItemProperty -Path $localMappingRegistryKey -Name Counter).Counter
    $localIndex = $localMapping.IndexOf($counterId)
    if ($localIndex -eq -1) {
        return $null
    }

    $localMapping[$localIndex + 1]
}

Write-Host '<<<iis_app_pool_state:sep(124)>>>'

$app_pool_was = Get-LocalizedEnglishPerfCounterName 'APP_POOL_WAS'
$current_application_pool_state = Get-LocalizedEnglishPerfCounterName 'Current Application Pool State'

if ($null -eq $app_pool_was -or $null -eq $current_application_pool_state) {
    exit
}

$AppPools = get-counter -Counter "\$app_pool_was(*)\$current_application_pool_state"
Foreach ($AppPool in $AppPools.CounterSamples) {
    if ($AppPool.InstanceName -eq "_total") {
        continue
    }
    Write-Host $AppPool.InstanceName"|"$AppPool.CookedValue
}
