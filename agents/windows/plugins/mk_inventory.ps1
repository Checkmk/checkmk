$name = (Get-Item env:\Computername).Value
$separator = "|"

# Processor
write-host "<<<win_cpuinfo:sep(58)>>>"
Get-WmiObject Win32_Processor -ComputerName $name | Select Name,Manufacturer,Caption,DeviceID,MaxClockSpeed,DataWidth,L2CacheSize,L3CacheSize,NumberOfCores,NumberOfLogicalProcessors,Status

# OS Version
write-host "<<<win_os:sep(58)>>>"
Get-WmiObject Win32_OperatingSystem -ComputerName $name -Recurse | foreach-object { write-host -separator $separator $_.csname, $_.caption, $_.version, $_.servicepackmajorversion, $_.ServicePackMinorVersion }

# Installed Software
write-host "<<<win_wmi_software:sep(124)>>>"
Get-WmiObject Win32_Product  -ComputerName $name | foreach-object { write-host -separator $separator $_.Name, $_.Vendor, $_.Version, $_.InstallDate }

## Search Registry
write-host "<<<win_reg_uninstall:sep(124)>>>"
Get-ChildItem "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall" -Recurse | foreach-object { write-host -separator $separator $_.PSChildName }

## Search exes
write-host "<<<win_exefiles:sep(124)>>>"
$paths = @("d:\", "c:\Program Files", "c:\Program Files (x86)", "c:\Progs")
foreach ($item in $paths)
{
    if ((Test-Path $item -pathType container))
    {
        Get-ChildItem -Path $item -include *.exe -Recurse | foreach-object { write-host -separator $separator $_.Fullname, $_.Length }
    }
}
