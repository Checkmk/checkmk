# Configuration
$delay = 14400 # execute agent only every $delay seconds
$exe_paths = @("c:\Program Files (x86)")

[System.Threading.Thread]::CurrentThread.CurrentCulture = [Globalization.CultureInfo]::InvariantCulture
[System.Threading.Thread]::CurrentThread.CurrentUICulture = [Globalization.CultureInfo]::InvariantCulture
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
write-output "" # workaround to prevent the byte order mark to be at the beginning of the first section
$name = (Get-Item env:\Computername).Value
$separator = "|"
# filename for timestamp
$remote_host = $env:REMOTE_HOST
$state_dir   = $env:MK_STATEDIR

# Fallback if the (old) agent does not provide the MK_STATEDIR
if (!$state_dir) {
    $state_dir = "c:\Program Files (x86)\check_mk\state"
}

$timestamp = $state_dir + "\timestamp."+ $remote_host

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
$cpu = Get-WmiObject Win32_Processor -ComputerName $name
$cpu_vars = @( "Name","Manufacturer","Caption","DeviceID","MaxClockSpeed","AddressWidth","L2CacheSize","L3CacheSize","Architecture","NumberOfCores","NumberOfLogicalProcessors","CurrentVoltage","Status" )
foreach ( $entry in $cpu ) { foreach ( $item in $cpu_vars) {  write-host $item ":" $entry.$item } }

# OS Version
write-host "<<<win_os:sep(124):persist($until)>>>"
Get-WmiObject Win32_OperatingSystem -ComputerName $name | foreach-object { write-host -separator $separator $_.csname, $_.caption, $_.version, $_.OSArchitecture, $_.servicepackmajorversion, $_.ServicePackMinorVersion, $_.InstallDate }

# Memory
#Get-WmiObject Win32_PhysicalMemory -ComputerName $name  | select BankLabel,DeviceLocator,Capacity,Manufacturer,PartNumber,SerialNumber,Speed

# BIOS
write-host "<<<win_bios:sep(58):persist($until)>>>"
$bios = Get-WmiObject win32_bios -ComputerName $name
$bios_vars= @( "Manufacturer","Name","SerialNumber","InstallDate","BIOSVersion","ListOfLanguages","PrimaryBIOS","ReleaseDate","SMBIOSBIOSVersion","SMBIOSMajorVersion","SMBIOSMinorVersion" )
foreach ( $entry in $bios ) { foreach ( $item in $bios_vars) {  write-host $item ":" $entry.$item } }

# System
write-host "<<<win_system:sep(58):persist($until)>>>"
$system = Get-WmiObject Win32_SystemEnclosure -ComputerName $name
$system_vars = @( "Manufacturer","Name","Model","HotSwappable","InstallDate","PartNumber","SerialNumber" )
foreach ( $entry in $system ) { foreach ( $item in $system_vars) {  write-host $item ":" $entry.$item } }

# Hard-Disk
write-host "<<<win_disks:sep(58):persist($until)>>>"
$disk = Get-WmiObject win32_diskDrive -ComputerName $name
$disk_vars = @( "Manufacturer","InterfaceType","Model","Name","SerialNumber","Size","MediaType","Signature" )
foreach ( $entry in $disk ) { foreach ( $item in $disk_vars) {  write-host $item ":" $entry.$item } }

# Graphics Adapter
write-host "<<<win_video:sep(58):persist($until)>>>"
$adapters=Get-WmiObject Win32_VideoController -ComputerName $name
$adapter_vars = @( "Name", "Description", "Caption", "AdapterCompatibility", "VideoModeDescription", "VideoProcessor", "DriverVersion", "DriverDate", "MaxMemorySupported")
foreach ( $entry in $adapters ) { foreach ( $item in $adapter_vars) {  write-host $item ":" $entry.$item } }

# Installed Software
write-host "<<<win_wmi_software:sep(124):persist($until)>>>"
Get-WmiObject Win32_Product -ComputerName $name | foreach-object { write-host -separator $separator $_.Name, $_.Vendor, $_.Version, $_.InstallDate }

# Search Registry
write-host "<<<win_reg_uninstall:sep(124):persist($until)>>>"
$paths = @("HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall")
foreach ($path in $paths) {
    Get-ChildItem $path -Recurse | foreach-object {  $path2 = $path+"\"+$_.PSChildName; get-ItemProperty -path $path2 |

        foreach-object {
        $Publisher = $_.Publisher -replace "`0", ""
        write-host -separator $separator $_.DisplayName, $Publisher , $_.InstallLocation, $_.PSChildName, $_.DisplayVersion, $_.EstimatedSize, $_.InstallDate }}
}

# Search exes
write-host "<<<win_exefiles:sep(124):persist($until)>>>"
foreach ($item in $exe_paths)
{
    if ((Test-Path $item -pathType container))
    {
        Get-ChildItem -Path $item -include *.exe -Recurse | foreach-object { write-host -separator $separator $_.Fullname, $_.LastWriteTime, $_.Length, $_.VersionInfo.FileDescription, $_.VersionInfo.ProduktVersion, $_.VersionInfo.ProduktName }
    }
}


