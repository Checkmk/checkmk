' MPIO_PATH_INFORMATION.vbs
' VBS WMI MPIO
' Author: Torsten Haake
' Date: 2011-02-15
' -----------------------------------------------'
Option Explicit
Const CMK_VERSION = "2.1.0p3"
Dim objWMIService, objItem, colItems, strComputer

' On Error Resume Next
strComputer = "."

' added for check_mk parsing (fh@mathias-ketter.de)
Wscript.Echo "<<<windows_multipath>>>"

' WMI connection to Root WMI
Set objWMIService = GetObject("winmgmts:\\" & strComputer & "\root\WMI")
Set colItems = objWMIService.ExecQuery("Select * from MPIO_PATH_INFORMATION")

For Each objItem in colItems
	Wscript.Echo objItem.NumberPaths
Next

WSCript.Quit

