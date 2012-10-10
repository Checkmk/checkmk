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
Dim windows_update_maxage, temp_file, new_file
Dim updtSearcher, colDownloads, objEntry, objFS, objShell, objFile

If CreateObject("Microsoft.Update.AutoUpdate").DetectNow <> 0 Then
  WScript.Echo "<<<windows_updates>>>"
  WScript.Quit(0)
End If

' Gathering the installed updates might take a lot of time, thus this
' check makes use of a cache. The cache saves and uses the current update 
' information for windows_updates_maxage seconds. After the file is too old
' the information are refreshed. The check is executed in "refresh" mode to
' update the data in background while the regular check still uses the current
' information. Once the update finished in the background job, the new data
' is used.

' Gather mode of the current script run
Dim mode
mode = "check"
If Wscript.Arguments.Count = 1 Then
	If Wscript.Arguments.Item(0) = "update" Then
		mode = "update"
	End If
End If

' Keep temporary file for 30 minutes
windows_update_maxage = 1800

Set objShell = CreateObject("WScript.Shell")
Set objFS = CreateObject("Scripting.FileSystemObject")

temp_file = objShell.ExpandEnvironmentStrings("%Temp%") & "\cmk_windows_updates_cache.txt"
new_file = objShell.ExpandEnvironmentStrings("%Temp%") & "\cmk_windows_updates_cache_new.txt"

Sub print_file(path)
    Set objFile = objFS.OpenTextFile(path, 1)
    Do Until objFile.AtEndOfStream
        wscript.echo objFile.ReadLine
    Loop
    objFile.Close
    Set objFile = nothing
End Sub

Sub start_update()
	' First create the new temp file (locks!)
    Set objFile = objFS.CreateTextFile(new_file, True)
    objFile.Close
    Set objFile = nothing
	
	' Now start the update in background (0: hide window, False: dont wait)
    objShell.Run Wscript.ScriptFullName + " update", 0, False
End Sub

Sub update()
    Set objFile = objFS.CreateTextFile(new_file, True)
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

	objFile.write("<<<windows_updates>>>" & vbCrLf)
	objFile.write(reboot & " " & numImp & " " & numOpt & vbCrLf)
	objFile.write(important & vbCrLf)
	objFile.write(opti)
	
    objFile.Close()
    Set objFile = nothing
	
	' After completion, move the file
	If objFS.FileExists(temp_file) Then
		objFS.DeleteFile(temp_file)
	End If
	objFS.MoveFile new_file, temp_file
End Sub

' Handle the update mode of this script. In this mode the new information
' are fetched via WMI. This should only be called in async mode because
' this might take a lot of time dependent on how many software is installed.
If mode = "update" Then
	update()
    WScript.Quit(0)
End If

If objFS.FileExists(temp_file) Then
    If DateDiff("s", objFS.GetFile(temp_file).DateLastModified, Now()) > windows_update_maxage Then
        ' Too old!
        If Not objFS.FileExists(new_file) Then
            ' Start fetching new data in the bakground
            start_update()
        End If
    End If

    ' Output current data if
    ' a) The temp_file is new enough
    ' b) The temp_file is too old but new data is being fetched now
    print_file temp_file
    WScript.Quit(0)
Else
    ' No data fetched yet,
    If Not objFS.FileExists(new_file) Then
        ' Start fetching new data in background
        start_update()
    End If

    ' Return empty
    WScript.Echo "<<<windows_updates>>>"
    WScript.Quit(0)
End If

Set objFS = nothing
Set objShell = nothing
WScript.Quit()