# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

$CMK_VERSION = "2.5.0b1"
$HKLM = "HKLM:\"

# These three lines are default in case not set in the agent bakery
$delay = 14400
$exePaths = @()
$regPaths = @("Software\Microsoft\Windows\CurrentVersion\Uninstall",
            "Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall")

$stateDir = [System.Environment]::GetEnvironmentVariable("MK_STATEDIR")
$confDir = [System.Environment]::GetEnvironmentVariable("MK_CONFDIR")
$remoteHost = [System.Environment]::GetEnvironmentVariable("REMOTE_HOST")

# Set values from the bakery configuration file
if($confDir){
    $confJson = Join-Path $confDir "mk_inventory_cfg.json"

    if(Test-Path $confJson){
        $jsonContent = Get-Content -Path $confJson -Raw
        $config = ConvertFrom-Json -InputObject $jsonContent
        if($config){
            $delay = $config.delay
            $exePaths = $config.exePaths
            $regPaths = $config.regPaths
        }
    }
}

# Default values if environment variables are missing
if (-not $remoteHost) {
    $remoteHost = "local"
}
# Fallback if an (old) agent does not provide the MK_STATEDIR
if ($confDir -and -not $stateDir) {
    $stateDir = $confDir
}

# Create timestamp only in case env variables are properly resolved
# Run script without a timestamp otherwise
if ($stateDir) {
    # Define timestamp file
    $timestamp = "$stateDir\mk_inventory.$($remoteHost -replace ':', '_')"

    # Check if timestamp file exists and its last modified time
    if (Test-Path $timestamp) {
        $fileDate = (Get-Item $timestamp).LastWriteTime
        # Exit if timestamp is too young
        if ($fileDate.AddSeconds($delay) -ge (Get-Date)) {
            exit
        }
    }

    # Create new timestamp file (requires admin rights)
    try {
        New-Item -Path $timestamp -ItemType File -Force | Out-Null
    }
    catch {
        Write-Output "Failed to create timestamp: $_"
    }
}

# The unix timestamp
$epoch = [int](([datetime]::UtcNow - [datetime] '1970-01-01').TotalSeconds)
# Convert add delay seconds plus 5 minutes
$timeUntil = $epoch + $delay + 300

function startSection {
    param (
        [string]$name,
        [string]$sep,
        [string]$timeUntil
    )
    Write-Output "<<<${name}:sep(${sep}):persist(${timeUntil})>>>"
}

function getWMIObject {
    param (
        [string]$strClass,
        [string[]]$arrVars
    )
    $entries = Get-CimInstance -ClassName $strClass -Namespace "root\cimv2"
    foreach ($entry in $entries) {
        $sortedProperties = $entry.PSObject.Properties |
        Where-Object { $_.Name -in $arrVars } |
        Sort-Object Name

        foreach ($property in  $sortedProperties) {
            if ($arrVars -contains $property.Name) {
                $value = $property.Value

                # Convert Date to the format expected by the parser
                if ($value -is [datetime]) {
                    $value = [System.Management.ManagementDateTimeConverter]::ToDmtfDateTime($value)
                }

                if ($value -is [array]) {
                    Write-Output("{0}: {1}" -f $property.Name, ($value -join " "))
                }
                else {
                    Write-Output("{0}: {1}" -f $property.Name, $value)
                }
            }
        }
    }
}

function getWMIObject2 {
    param (
        [string]$ClassName,
        [string[]]$arrVars
    )
    $entries = Get-CimInstance -ClassName $ClassName -Namespace "root\cimv2"
    foreach ($entry in $entries) {
        $values = @()
        foreach ($label in $arrVars) {
            $property = $entry.PSObject.Properties[$label]
            $value = if ($property) { $property.Value } else { "" }

            # Convert Date to the format expected by the parser
            if ($value -is [datetime]) {
                $value = [System.Management.ManagementDateTimeConverter]::ToDmtfDateTime($value)
            }

            # Append Update Build Revision (UBR) to the version property
            if ($label -eq "version") {
                $ubr = (Get-ItemProperty -Path "${HKLM}SOFTWARE\Microsoft\Windows NT\CurrentVersion").UBR
                if($ubr){
                    $value = "$value.$ubr"
                }
            }

            $values += $value
        }
        Write-Output ($values -join "|")
    }
}

function getNetworkAdapter {
    param (
        [string[]]$arrVars
    )
    $adapters = Get-CimInstance -ClassName "Win32_NetworkAdapter" -Namespace "root\cimv2"
    $adapterConfigs = Get-CimInstance -ClassName "Win32_NetworkAdapterConfiguration" -Namespace "root\cimv2"
    foreach ($adapter in $adapters) {
        # Only handle Adapters with a MAC address and exclude AsyncMac
        if ($adapter.ServiceName -ne "AsyncMac" -and -not [string]::IsNullOrEmpty($adapter.MACAddress)) {
            $sortedProperties = $adapter.PSObject.Properties |
            Where-Object { $_.Name -in $arrVars } |
            Sort-Object Name
            foreach ($property in $sortedProperties) {
                if ($arrVars -contains $property.Name) {
                    if ($property.Value -is [array]) {
                        Write-Output ("{0}: {1}" -f $property.Name, ($property.Value -join " "))
                    }
                    else {
                        Write-Output ("{0}: {1}" -f $property.Name, $property.Value)
                    }
                }
            }
            # Find matching network adapter configuration
            $adapterConfig = $adapterConfigs | Where-Object { $_.Description -eq $adapter.Name }
            if ($adapterConfig) {
                if ($adapterConfig.IPAddress) {
                    Write-Output ("Address: {0}" -f ($adapterConfig.IPAddress -join " "))
                }
                if ($adapterConfig.IPSubnet) {
                    Write-Output ("Subnet: {0}" -f ($adapterConfig.IPSubnet -join " "))
                }
                if ($adapterConfig.DefaultIPGateway) {
                    Write-Output ("DefaultGateway: {0}" -f ($adapterConfig.DefaultIPGateway -join " "))
                }
            }
        }
    }
}

function getRouteTable {
    $adapters = Get-CimInstance -ClassName "Win32_NetworkAdapter" -Namespace "root\cimv2"
    $routes = Get-CimInstance -ClassName "Win32_IP4RouteTable" -Namespace "root\cimv2"

    $indexNames = @{}
    foreach ($adapter in $adapters) {
        $indexNames[[int]$adapter.InterfaceIndex] = $adapter.Name
    }

    $routeTypes = @{
        1 = "other"
        2 = "invalid"
        3 = "direct"
        4 = "indirect"
    }

    foreach ($route in $routes) {
        $rtType = [string]$routeTypes[[int]$route.Type]
        $rtGateway = $route.NextHop
        $rtTarget = $route.Destination
        $rtMask = $route.Mask
        $rtDevice = [string]$indexNames[[int]$route.InterfaceIndex]
        if ($rtDevice) {
            Write-Output ("{0}|{1}|{2}|{3}|{4}" -f $rtType, $rtTarget, $rtMask, $rtGateway, $rtDevice)
        }
    }
}

function getSoftwareFromInstaller {
    param (
        [string[]]$fields
    )
    $WI_SID_EVERYONE = "s-1-1-0"
    $WI_ALL_CONTEXTS = 7
    # Create Windows Installer COM object
    $installer = New-Object -ComObject WindowsInstaller.Installer
    # Try getting products using ProductsEx
    try {
        $products = $installer.ProductsEx("", $WI_SID_EVERYONE, $WI_ALL_CONTEXTS)
        $productsEx = $true
    }
    catch {
        $productsEx = $false
        try {
            $products = $installer.Products()
        }
        catch {
            # Exit here, because we are unable to query the installed software
            # Write-Output "Cannot list installed software"
            return
        }
    }
    # Iterate over installed software
    foreach ($item in $products) {
        try {
            if ($productsEx) {
                # Using ProductsEx method
                $product = $item
                $productCode = $product.ProductCode
                $values = @()
                foreach ($field in $fields) {
                    $values += $product.InstallProperty($field)
                }
                Write-Output ($values -join "$([char]31)")
            }
            else {
                # Using Products method
                $productCode = $item
                $values = @()
                foreach ($field in $fields) {
                    $values += $installer.ProductInfo($productCode, $field)
                }
                Write-Output ($values -join "$([char]31)")
            }
        }
        catch {
            # Ignore errors and continue
            continue
        }
    }
}

function getUpdates {
    Write-Output "Node,Description,HotFixID,InstalledOn"
    $computerName = (Get-CimInstance Win32_ComputerSystem).Name
    Get-HotFix | ForEach-Object {
        $installedOn = $_.InstalledOn
        if ($installedOn -is [datetime]) {
            # Remove leading zeros using 'M/d/yyyy'
            $installedOn = $installedOn.ToString("M/d/yyyy")
        }
        Write-Output "$computerName,$($_.Description),$($_.HotFixID),$($installedOn)"
    }
}

function EscapeRegistryPath {
    param (
        [string]$Path
    )
    return $Path -replace '([]`*\?\[""])', '`$1'
}

function getSoftwareFromRegistry {
    $regVars = @("DisplayName", "Publisher", "InstallLocation", "PSChildName", "DisplayVersion", "EstimatedSize", "InstallDate", "Language")

    foreach ($path in $regPaths) {
        $machineHivePath = "$HKLM$path"
        if (Test-Path $machineHivePath) {
            $subkeys = Get-ChildItem -Path $machineHivePath

            foreach ($subkey in $subkeys) {
                $values = @()
                $booleanContent = $false

                foreach ($var in $regVars) {
                    $escapedRegistryPath = EscapeRegistryPath $subkey.PSPath
                    if ($var -eq "PSChildName") {
                        $value = $subkey.PSChildName
                    }
                    elseif ($var -eq "Language") {
                        $value = (Get-ItemProperty -Path $escapedRegistryPath -Name $var -ErrorAction SilentlyContinue).$var
                        if ($null -ne $value) {
                            $value = $value.ToString()
                        }
                    }
                    else {
                        $value = (Get-ItemProperty -Path $escapedRegistryPath -Name $var -ErrorAction SilentlyContinue).$var
                    }

                    if ($null -ne $value -and $value -is [string]) {
                        $values += $value
                        if ($var -ne "PSChildName") {
                            $booleanContent = $true
                        }
                    }
                    else {
                        $values += ""  # Ensure empty placeholders are present
                    }
                }

                if ($booleanContent) {
                    Write-Output ($values -join "$([char]31)")
                }
            }
        }
    }
}

function recurseFolderForExecs {
    param (
        [string]$folderPath
    )

    # Get all files in the current folder
    Get-ChildItem -Path $folderPath -File | ForEach-Object {
        # Check if the file has an extension and if it's ".exe"
        if ($_.Extension -eq ".exe") {
            # Get file version (if available)
            $fileVersion = (Get-Item $_.FullName).VersionInfo.FileVersionRaw

            # Output file details
            Write-Output ("$($_.FullName)|$(Get-Date $_.LastWriteTime -Format 'M/d/yyyy HH:mm:ss')|$($_.Length)||$fileVersion|")
        }
    }

    # Recursively process subfolders
    Get-ChildItem -Path $folderPath -Directory | ForEach-Object {
        recurseFolderForExecs $_.FullName
    }
}

function getSoftwareFromFilesystem {
    foreach ($path in $exePaths) {
        if (Test-Path -Path $path -PathType Container) {
            recurseFolderForExecs $path
        }
    }
}

# Processor
startSection "win_cpuinfo" 58 $timeUntil
getWMIObject "Win32_Processor" @("Name", "Manufacturer", "Caption", "DeviceID", "MaxClockSpeed", "AddressWidth", "L2CacheSize", "L3CacheSize", "Architecture", "NumberOfCores", "NumberOfLogicalProcessors", "CurrentVoltage", "Status")

# OS Version
startSection "win_os" 124 $timeUntil
getWMIObject2 "Win32_OperatingSystem" @("csname", "caption", "version", "OSArchitecture", "servicepackmajorversion", "ServicePackMinorVersion", "InstallDate")

# Memory
# startSection "win_memory" 58 $timeUntil
# getWMIObject "Win32_PhysicalMemory" @("BankLabel","DeviceLocator","Capacity","Manufacturer","PartNumber","SerialNumber","Speed")

# BIOS
startSection "win_bios" 58 $timeUntil
getWMIObject "Win32_bios" @("Manufacturer", "Name", "SerialNumber", "InstallDate", "BIOSVersion", "ListOfLanguages", "PrimaryBIOS", "ReleaseDate", "SMBIOSBIOSVersion", "SMBIOSMajorVersion", "SMBIOSMinorVersion")

# System
startSection "win_system" 58 $timeUntil
getWMIObject "Win32_SystemEnclosure" @("Manufacturer", "Name", "Model", "HotSwappable", "InstallDate", "PartNumber", "SerialNumber")

# ComputerSystem
startSection "win_computersystem" 58 $timeUntil
getWMIObject "Win32_ComputerSystem" @("Manufacturer", "Name", "Model", "InstallDate")

# ComputerSystemProduct
startSection "win_computersystemproduct" 58 $timeUntil
getWMIObject "Win32_ComputerSystemProduct" @("UUID")

# Hard-Disk
startSection "win_disks" 58 $timeUntil
getWMIObject "Win32_diskDrive" @("Manufacturer", "InterfaceType", "Model", "Name", "SerialNumber", "Size", "MediaType", "Signature")

# Graphics Adapter
startSection "win_video" 58 $timeUntil
getWMIObject "Win32_VideoController" @("Name", "Description", "Caption", "AdapterCompatibility", "VideoModeDescription", "VideoProcessor", "DriverVersion", "DriverDate", "MaxMemorySupported", "AdapterRAM")

# Network Adapter
startSection "win_networkadapter" 58 $timeUntil
getNetworkAdapter @("Name", "ServiceName", "MACAddress", "AdapterType", "DeviceID", "NetworkAddresses", "Speed")

# Route Table
startSection "win_ip_r" 124 $timeUntil
getRouteTable

# Installed Software
startSection "win_wmi_software" 31 $timeUntil
getSoftwareFromInstaller @("ProductName", "Publisher", "VersionString", "InstallDate", "Language")

# Windows Updates
startSection "win_wmi_updates" 44 $timeUntil
getUpdates

# Search Registry
startSection "win_reg_uninstall" 31 $timeUntil
getSoftwareFromRegistry

# Search exes
startSection "win_exefiles" 124 $timeUntil
getSoftwareFromFilesystem
