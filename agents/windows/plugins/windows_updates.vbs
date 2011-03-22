' -----------------------------------------------------------------------------
' windows_updates.vbs - check_mk agent plugin to monitor pending windows updates
'
' To use this just place it in the plugins/ directory below the path of the
' check_mk_agent. After that an inventory run on the Nagios host should lead
' to a new inventorized service.
'
' Author: Lars Michelsen <lm@mathias-kettner.de>, 2011-03-21
' -----------------------------------------------------------------------------

Option Explicit

Dim result, reboot, numImp, numOpt, important, opti
Dim updtSearcher, colDownloads, objEntry

If CreateObject("Microsoft.Update.AutoUpdate").DetectNow <> 0 Then
  WScript.Echo "<<<windows_updates>>>"
  WScript.Quit(0)
End If

Set updtSearcher = CreateObject("Microsoft.Update.Session").CreateUpdateSearcher

reboot = 0
numImp = 0
numOpt = 0

If CreateObject("Microsoft.Update.SystemInfo").RebootRequired Then
  reboot = 1
End If

Set result = updtSearcher.Search("IsInstalled = 0 and IsHidden = 0")
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

WScript.Echo "<<<windows_updates>>>"
WScript.Echo reboot & " " & numImp & " " & numOpt
WScript.Echo important
WScript.Echo opti
WScript.Quit()
