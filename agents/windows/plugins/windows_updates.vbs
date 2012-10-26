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
' -----------------------------------------------------------------------------------------

Option Explicit

Dim result, reboot, numImp, numOpt, important, opti
Dim updtSearcher, colDownloads, objEntry

Dim objFSO, objFile 
Set objFSO = WScript.CreateObject("Scripting.FileSystemObject")

Dim lastModificationDate
Dim updateNeeded
updateNeeded = True

Dim WSHShell
Set WSHShell = CreateObject("WScript.Shell")

Dim scriptname, scriptpath, strFolder

scriptname = Wscript.ScriptFullName
scriptpath = objFSO.getparentfoldername(scriptname)

strFolder = scriptpath & "\windows-update"
set objFSO = createobject("Scripting.FileSystemObject")

if objFSO.FolderExists(strFolder) = False then
	objFSO.CreateFolder strFolder
end if

Dim ts, TextLine
Dim rndFudge

Randomize
rndFudge = Int(8 * 60 * Rnd) ' random fudge factor for test (0 to 8 hrs) 

If objFSO.FileExists(scriptpath &"\windows-update\windows_updates-log.txt") Then
	lastModificationDate = objFSO.GetFile(scriptpath &"\windows-update\windows_updates-log.txt").DateLastModified
	If DateDiff("n", lastModificationDate, now) < ((60*24)-rndFudge) Then ' 1 day minus 0 to 8 hours
	  updateNeeded = False
	End If
End If

If updateNeeded Then 
    Set objFile = objFSO.CreateTextFile(scriptpath &"\windows-update\windows_updates-log.txt")

    If CreateObject("Microsoft.Update.AutoUpdate").DetectNow <> 0 Then
      objFile.WriteLine("<<<windows_updates>>>")
      WScript.Quit()
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

    objFile.WriteLine("<<<windows_updates>>>")
    objFile.WriteLine(reboot & " " & numImp & " " & numOpt)
    objFile.WriteLine(important)
    objFile.WriteLine(opti)
    objFile.Close

End If

Set ts = objFSO.GetFile(scriptpath &"\windows-update\windows_updates-log.txt").OpenAsTextStream(1, -2)
Do While ts.AtEndOfStream <> True
		WScript.Echo ts.ReadLine
Loop
ts.Close

WScript.Quit()
