$name = (Get-Item env:\Computername).Value
$separator = "|"
# filename for timestamp
$remote_host = $env:REMOTE_HOST
$timestamp = "c:\Program Files (x86)\Check_mk\timestamp.$remote_host"
# execute agent only every $delay seconds
$delay = 1

# does $timestamp exist?
If (Test-Path $timestamp){
    $filedate = (ls $timestamp).LastWriteTime
    $now = Get-Date
    $earlier = $now.AddSeconds(-$delay)
    # exit if timestamp to young
    if ( $filedate -gt $earlier ) { exit }
}
# create new timestamp file
New-Item $timestamp -type file -force | Out-Null

# calculate unix timestamp
$epoch=[int][double]::Parse($(Get-Date -date (Get-Date).ToUniversalTime()-uformat %s))

# convert it to integer and add $delay seconds plus 5 minutes
$until = [int]($epoch -replace ",.*", "") + $delay + 600

# Processor
write-host "<<<win_cpuinfo:sep(58):persist($until)>>>"
Get-WmiObject Win32_Processor -ComputerName $name | Select Name,Manufacturer,Caption,DeviceID,MaxClockSpeed,AddressWidth,L2CacheSize,L3CacheSize,Architecture,NumberOfCores,NumberOfLogicalProcessors,CurrentVoltage,Status

# OS Version
write-host "<<<win_os:sep(124):persist($until)>>>"
Get-WmiObject Win32_OperatingSystem -ComputerName $name -Recurse | foreach-object { write-host -separator $separator $_.csname, $_.caption, $_.version, $_.OSArchitecture, $_.servicepackmajorversion, $_.ServicePackMinorVersion }

# Memory
#Get-WmiObject Win32_PhysicalMemory -ComputerName $name  | select BankLabel,DeviceLocator,Capacity,Manufacturer,PartNumber,SerialNumber,Speed

# BIOS
write-host "<<<win_bios:sep(58)>>>"
Get-WmiObject win32_bios -ComputerName $name  | Select Manufacturer,Name,SerialNumber,InstallDate,BIOSVersion,ListOfLanguages,PrimaryBIOS,ReleaseDate,SMBIOSBIOSVersion,SMBIOSMajorVersion,SMBIOSMinorVersion

# System
write-host "<<<win_system:sep(58)>>>"
Get-WmiObject Win32_SystemEnclosure -ComputerName $name  | Select Manufacturer,Name,Model,HotSwappable,InstallDate,PartNumber,SerialNumber

# Hard-Disk
write-host "<<<win_disk:sep(58)>>>"
Get-WmiObject win32_diskDrive -ComputerName $name  | select Manufacturer,Model,Name,SerialNumber,InterfaceType,Size,Partitions

# Graphics Adapter
write-host "<<<win_video:sep(58)>>>"
Get-WmiObject Win32_VideoController -ComputerName $name | Select Name, Description, Caption, AdapterCompatibility, VideoModeDescription, VideoProcessor, DriverVersion, DriverDate, MaxMemorySupported


# Installed Software
write-host "<<<win_wmi_software:sep(124):persist($until)>>>"
Get-WmiObject -Class Win32_Product  -ComputerName $name | foreach-object { write-host -separator $separator $_.Name, $_.Vendor, $_.Version, $_.InstallDate }
Get-WmiObject Win32_Product  -ComputerName $name | foreach-object { write-host -separator $separator $_.Name, $_.Vendor, $_.Version, $_.InstallDate }

## Search Registry
write-host "<<<win_reg_uninstall:sep(124):persist($until)>>>"
Get-ChildItem "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall" -Recurse | foreach-object { write-host -separator $separator $_.PSChildName }

## Search exes
write-host "<<<win_exefiles:sep(124):persist($until)>>>"
$paths = @("d:\", "c:\Program Files", "c:\Program Files (x86)", "c:\Progs")
foreach ($item in $paths)
{
    if ((Test-Path $item -pathType container))
    {
        Get-ChildItem -Path $item -include *.exe -Recurse | foreach-object { write-host -separator $separator $_.Fullname, $_.Length }
    }
}


