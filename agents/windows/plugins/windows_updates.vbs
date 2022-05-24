' -----------------------------------------------------------------------------------------
' windows_updates.vbs - check_mk agent plugin to monitor pending windows updates indirectly
'
' To use this just place it in the plugins/ directory below the path of the
' check_mk_agent. After that an inventory run on the Nagios host should lead
' to a new inventorized service.
'
' Author: Lars Michelsen <lm@mathias-kettner.de>, 2011-03-21
' Editor: Patrick Schlüter <ps@pdv-systeme.de>, 2011-08-21
'
' Updated by Phil Randal, 2012-09-21, to cache results using a randomised check interval
' of 16 to 24 hours
' Based on code here: http://www.monitoring-portal.org/wbb/index.php?page=Thread&threadID=23509
' Spawning a separate process to produce cached result (as in above forum discussion) caused me
' some issues, so I went for a simpler solution using only one script
'
' Updated by Bastian Kuhn, 2014-03-03: Removed all caching functions cause the current agent
' has a native caching support. Make sure that you activate caching for this script in check_mk.ini
'
' 2014-04-17: Fix by Stefan Kick to handle errors. Payed by Adaptron.
' -----------------------------------------------------------------------------------------

Option Explicit
Const CMK_VERSION = "2.0.0p26"

Dim fso
Dim objStdout
Set fso = CreateObject("Scripting.FileSystemObject")
' request unicode stdout and add a bom so the agent knows we send utf-16
Set objStdout = fso.GetStandardStream(1, True)
objStdout.Write(chrW(&HFEFF))

function readFromRegistry (strRegistryKey, strDefault )
    Dim WSHShell, value

    On Error Resume Next
    Set WSHShell = CreateObject("WScript.Shell")
    value = WSHShell.RegRead( strRegistryKey )

    if err.number <> 0 then
        readFromRegistry=strDefault
    else
        readFromRegistry=value
    end if

    set WSHShell = nothing
end function

Dim result, reboot, numImp, numOpt, important, opti
Dim updtSearcher, colDownloads, objEntry


Dim WSHShell
Set WSHShell = CreateObject("WScript.Shell")

Dim RebootTime
Dim RegPath


If CreateObject("Microsoft.Update.AutoUpdate").DetectNow <> 0 Then
    objStdout.WriteLine "<<<windows_updates>>>"
    WScript.Quit()
End If

Set updtSearcher = CreateObject("Microsoft.Update.Session").CreateUpdateSearcher

RegPath = "HKEY_LOCAL_MACHINE\SOFTWARE\MICROSOFT\Windows\CurrentVersion\WindowsUpdate\Auto Update\"
RebootTime = ReadFromRegistry(RegPath & "NextFeaturedUpdatesNotificationTime","no_key")

reboot = 0
numImp = 0
numOpt = 0

If CreateObject("Microsoft.Update.SystemInfo").RebootRequired Then
    reboot = 1
End If

On Error Resume Next

Set result = updtSearcher.Search("IsInstalled = 0 and IsHidden = 0")

If Err.Number <> 0 then
        objStdout.WriteLine "<<<windows_updates>>>"
        objStdout.WriteLine "x x x"
        objStdout.WriteLine "There was an error getting update information. Maybe Windows update is not activated. Error Number: " & Err.Number
        WScript.Quit()
End If


Set colDownloads = result.Updates
For Each objEntry in colDownloads

    if objEntry.AutoSelectOnWebSites Then
       if numImp = 0 Then
           important = objEntry.Title
       else
           important = important & "; " & objEntry.Title
    End If
        numImp = numImp + 1
    Else
        If numOpt = 0 Then
            opti = objEntry.Title
        Else
            opti = opti & "; " & objEntry.Title
        End If
        numOpt = numOpt + 1
    End If

Next

objStdout.WriteLine "<<<windows_updates>>>"
objStdout.WriteLine reboot & " " & numImp & " " & numOpt
objStdout.WriteLine important
objStdout.WriteLine opti
objStdout.WriteLine RebootTime
WScript.Quit()
