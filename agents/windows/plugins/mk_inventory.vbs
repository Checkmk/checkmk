CONST HKLM = &H80000002

Dim delay
Dim exePaths
Dim regPaths

' these three lines are set in the agent bakery
delay = 14400
exePaths = Array("")
regPaths = Array("Software\Microsoft\Windows\CurrentVersion\Uninstall","Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall")

Set fso = CreateObject("Scripting.FileSystemObject")
' request unicode stdout and add a bom so the agent knows we send utf-16
Set objStdout = fso.GetStandardStream(1, True)
objStdout.Write(chrW(&HFEFF))
Set objClass = GetObject("winmgmts:{impersonationLevel=impersonate}!\\.\root\cimv2")
Set wshShell = WScript.CreateObject( "WScript.Shell" )
remote_host = wshShell.ExpandEnvironmentStrings( "%REMOTE_HOST%" )
If remote_host = "%REMOTE_HOST%" Then
	remote_host = "local"
End If
state_dir   = wshShell.ExpandEnvironmentStrings( "%MK_STATEDIR%" )
conf_dir   = wshShell.ExpandEnvironmentStrings( "%MK_CONFDIR%" )

' Fallback if an (old) agent does not provide the MK_STATEDIR
If state_dir = "%MK_STATEDIR%" Then
    state_dir = conf_dir
End If

' to be able to quickly change the output function
Sub outPut(strOut)
    'WScript.Echo strOut
    objStdout.WriteLine strOut
End Sub

timestamp = state_dir & "\mk_inventory." & Replace(remote_host, ":", "_")

' does timestamp exist?
If (fso.FileExists(timestamp)) Then
    Set objTimestamp = fso.GetFile(timestamp)
    fileDate = objTimestamp.DateLastModified
    ' exit if timestamp is too young
    If DateAdd("s", delay, filedate) >= Now Then
        WScript.Quit
    End If
End If


' handle error message ourselves so this script can also be run directly, for testing
On Error Resume Next


' create new timestamp file
' only allowed when script runs as administrator user
Set stampo = fso.CreateTextFile(timestamp)

If Err.Number <> 0 Then
    outPut "Failed to create time stamp: " & Err.Description & " (" & Err.Number & ")" 
    Err.Clear
End If

On Error Goto 0


' determine the timezone offset w/t GMT
Set systemParams = objClass.ExecQuery("Select * from Win32_ComputerSystem")
For Each param in systemParams
    offset = param.CurrentTimeZone
    Exit For
Next

' the unix timestamp
epoch = DateDiff("s", "01/01/1970 00:00:00", Now()) - (offset * 60)

' convert add delay seconds plus 5 minutes
timeUntil = epoch + delay + 300

Sub startSection(name,sep,timeUntil)
    outPut("<<<" & name & ":sep(" & sep & "):persist(" & timeUntil & ")>>>")
End Sub

Sub getWMIObject(strClass,arrVars)
    Set objClass = GetObject("winmgmts:{impersonationLevel=impersonate}!\\.\root\cimv2")
    Set Entries = objClass.ExecQuery("Select * from " & strClass)
    For Each entry in Entries
        For Each item in entry.Properties_
            ' if it is in arrVars
            If UBound(filter(arrVars, item.name)) = 0 Then
                If isArray(item.value) Then
                    outPut(item.name & ": " & join(item.value))
                Else
                    outPut(item.name & ": " & item.value)
                End If
            End If
        Next
    Next
End Sub

Sub getWMIObject2(strClass,arrVars)
    Set Entries = objClass.ExecQuery("Select * from " & strClass)
    For Each entry in Entries
        strTemp = "A"
        For Each label in arrVars
            strTemp = strTemp & "|"
            For Each item in entry.Properties_
                If LCase(item.name) = LCase(label) Then
                    strTemp = strTemp & item.value
                End If
            Next
        Next
        outPut(Mid(strTemp,3))
    Next
End Sub

Sub RecurseForExecs(strFolderPath)
    Dim objFolder
    Set objFolder = fso.GetFolder(strFolderPath)
    Dim objFile
    Dim objSubFolder
    For Each objFile In objFolder.Files
        'only proceed if there is an extension on the file.
        If (InStr(objFile.Name, ".") > 0) Then
            'If the file's extension is "exe", write the path to the output file.
            If (LCase(Mid(objFile.Name, InStrRev(objFile.Name, "."))) = ".exe") Then
                outPut(objFile.Path & "|" & objFile.DateLastModified & "|" & objFile.Size & "|" & "" & "|" & fso.GetFileVersion(objFile.path) & "|")
            End If
        End If
    Next

    For Each objSubFolder In objFolder.SubFolders
        Call RecurseForExecs(objSubFolder.Path)
    Next
End Sub

Sub SoftwareFromInstaller(fields)
    Dim installer
    Set installer = CreateObject("WindowsInstaller.Installer")
    Dim productCode, productName
    For Each productCode In installer.Products
        values = fields  ' copy
        idx = 0

        For Each field In fields
            values(idx) = installer.ProductInfo(productCode, field)
            idx = idx + 1
        Next
        outPut(Join(values, "|"))
    Next
End Sub

' Processor
Call startSection("win_cpuinfo",58,timeUntil)
cpuVars = Array( "Name","Manufacturer","Caption","DeviceID","MaxClockSpeed","AddressWidth","L2CacheSize","L3CacheSize","Architecture","NumberOfCores","NumberOfLogicalProcessors","CurrentVoltage","Status" )
Call getWMIObject("Win32_Processor",cpuVars)

' OS Version
Call startSection("win_os",124,timeUntil)
osVars = Array( "csname", "caption", "version", "OSArchitecture", "servicepackmajorversion", "ServicePackMinorVersion", "InstallDate" )
Call getWMIObject2("Win32_OperatingSystem",osVars)

' Memory
'Get-WmiObject Win32_PhysicalMemory -ComputerName $name  | select BankLabel,DeviceLocator,Capacity,Manufacturer,PartNumber,SerialNumber,Speed

' BIOS
Call startSection("win_bios",58,timeUntil)
biosVars = Array( "Manufacturer","Name","SerialNumber","InstallDate","BIOSVersion","ListOfLanguages","PrimaryBIOS","ReleaseDate","SMBIOSBIOSVersion","SMBIOSMajorVersion","SMBIOSMinorVersion" )
Call getWMIObject("Win32_bios",biosVars)

' System
Call startSection("win_system",58,timeUntil)
systemVars = Array( "Manufacturer","Name","Model","HotSwappable","InstallDate","PartNumber","SerialNumber" )
Call getWMIObject("Win32_SystemEnclosure",systemVars)

' Hard-Disk
Call startSection("win_disks",58,timeUntil)
diskVars = Array( "Manufacturer","InterfaceType","Model","Name","SerialNumber","Size","MediaType","Signature" )
Call getWMIObject("Win32_diskDrive",diskVars)

' Graphics Adapter
Call startSection("win_video",58,timeUntil)
adapterVars = Array( "Name", "Description", "Caption", "AdapterCompatibility", "VideoModeDescription", "VideoProcessor", "DriverVersion", "DriverDate", "MaxMemorySupported")
Call getWMIObject("Win32_VideoController",adapterVars)

' Installed Software
Call startSection("win_wmi_software",124,timeUntil)
swVars = Array( "ProductName", "Publisher", "VersionString", "InstallDate", "Language")
Call SoftwareFromInstaller(swVars)

' Search Registry
Call startSection("win_reg_uninstall",124,timeUntil)
Set rego = GetObject("WinMgmts:{impersonationLevel=impersonate}!\\.\root\default:StdRegProv")
regVars = Array("DisplayName", "Publisher", "InstallLocation", "PSChildName", "DisplayVersion", "EstimatedSize", "InstallDate", "Language")

For Each path in regPaths
    rego.EnumKey HKLM, path, arrIdentityCode
    If isArray(arrIdentityCode) Then
        For Each strIdentityCode in arrIdentityCode
            strOut = ""
            boleanContent = False
            For Each var in regVars
                ' PSChildName is the name in powershell
                ' we use strIdentityCode in vbs
                If var = "PSChildName" Then
                    value = strIdentityCode
                ' Language is a DWord
                ElseIf var = "Language" Then
                    intResult = rego.GetDWordValue(HKLM, path & "\" & strIdentityCode, var, value)
                ' Everything else hopefully is a string
                Else
                    intResult = rego.GetStringValue(HKLM, path & "\" & strIdentityCode, var, value)
                End If
                ' only allow vartypes which can be represented as a string
                If VarType(value) <= 8 and VarType(value) > 1 Then
                    strOut = strOut & "|" & CStr(value)
                    ' only print a line when more than only PSChildName is present
                    If var <> "PSChildName" Then
                        boleanContent = True
                    End If
                Else
                    strOut = strOut & "|"
                End If
            Next
            If boleanContent Then
                outPut(Mid(strOut,2))
            End If
        Next
    End If
Next

' Search exes
Call startSection("win_exefiles",124,timeUntil)
For Each path in exePaths
    If fso.FolderExists(path) Then
        Call RecurseForExecs(path)
    End If
Next

WScript.Quit()
