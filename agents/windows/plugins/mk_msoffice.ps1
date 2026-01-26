# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

$CMK_VERSION = "2.4.0p21"
$MK_CONFDIR = $env:MK_CONFDIR
$ClientId = ""
$TenantId = ""
$ClientSecret = ""

# Microsoft.Graph module is required for all users, please install
if (-not (Get-Module -ListAvailable -Name Microsoft.Graph)) {
    Write-Host "<<<msoffice_licenses>>>"
    Write-Host "Microsoft.Graph module is not installed, exiting."
    Write-Host "<<<msoffice_serviceplans>>>"
    Write-Host "Microsoft.Graph module is not installed, exiting."
    exit
}

if(-not $MK_CONFDIR) {
    Write-Host '$env:MK_CONFDIR is not initialized, it should point to %SystemDrive%\ProgramData\checkmk\agent\config, exiting.'
    exit
}

$confJson = Join-Path $MK_CONFDIR "msoffice_cfg.json"

if(-not (Test-Path $confJson)) {
    Write-Host "Configuration file msoffice_cfg.json not found in $MK_CONFDIR, exiting."
    exit
}

$jsonContent = Get-Content -Path $confJson -Raw
$config = ConvertFrom-Json -InputObject $jsonContent
if(-not $config) {
    Write-Host "Failed to parse JSON configuration from the ${MK_CONFDIR}\msoffice_cfg.json, exiting."
    exit
}

$ClientId = $config.ClientId
$TenantId = $config.TenantId
$ClientSecret = $config.ClientSecret

if ([string]::IsNullOrEmpty($ClientId) -or
    [string]::IsNullOrEmpty($TenantId) -or
    [string]::IsNullOrEmpty($ClientSecret)) {
    Write-Host "One or more required credentials are empty, check your configuration in ${MK_CONFDIR}\msoffice_cfg.json."
    exit
}

try {
    $SecureClientSecret = ConvertTo-SecureString -String $ClientSecret -AsPlainText -Force
    $ClientSecretCredential = New-Object -TypeName System.Management.Automation.PSCredential -ArgumentList $ClientId, $SecureClientSecret
    Connect-MgGraph -TenantId $TenantId -ClientSecretCredential $ClientSecretCredential -NoWelcome -ErrorAction Stop
} catch {
    Write-Host "Failed to connect to Microsoft Graph: $_"
    exit
}

try {
    $licenses = Get-MgSubscribedSku -ErrorAction Stop
} catch {
    Write-Host "Failed to fetch licenses: $_"
    exit
}

Write-Host "<<<msoffice_licenses>>>"
foreach ($license in $licenses) {
    $line = "mggraph:{0} {1} {2} {3}" -f $license.SkuPartNumber, $license.PrepaidUnits.Enabled, $license.PrepaidUnits.Warning, $license.ConsumedUnits
    Write-Host $line
}

Write-Host "<<<msoffice_serviceplans>>>"
foreach ($license in $licenses) {
    foreach ($serviceplan in $license.ServicePlans) {
        $line = "mggraph:{0} {1} {2}" -f $license.SkuPartNumber, $serviceplan.ServicePlanName, $serviceplan.ProvisioningStatus
        Write-Host $line
    }
}

Disconnect-MgGraph | Out-Null
