' Check for citrix licenses
' This is an almost unmodified version of ctx_licensecheck.vbs from Stefan Senftleben.
Const CMK_VERSION = "2.1.0b9"
On Error Resume Next
Dim objWMI : Set objWMI = GetObject("winmgmts:\\" & strComputer)
Dim strComputer : strComputer = "."
Set objService = GetObject("winmgmts:\\" & strComputer & "\root\CitrixLicensing")
Set colItems = objService.ExecQuery("SELECT * FROM Citrix_GT_License_Pool",,48)
Wscript.Echo "<<<citrix_licenses>>>"
For Each objItem in colItems
        WScript.Echo objItem.PLD & vbTab & objItem.Count & vbTab & objItem.InUseCount
Next
