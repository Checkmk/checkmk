' This script can be used to update the installer database after it is built - see CustomMessages.wxl for related code.
' Add a Post-build event to the ExcelAddInDeploy project: 
' Cscript "{Path to WiRunSQL.vbs}\WiRunSQL.vbs" "$(TargetDir)en-us\$(TargetFileName)" "UPDATE `TextStyle` SET `Color` = 16777215 WHERE `TextStyle` = 'WixUI_Font_Title'"
' This updates the installer database after it is built and changes the colour of the title text.  Note the use of ` not ' around field names.  Colour value calculated as:

' "65536 * blue + 256 * green + red, where red, green, and blue are each in the range of 0-255. The value must not exceed 16777215, which is the value for white. 
' The value is 0 for black, 255 for red, 65280 for green, 16711680 for blue and 8421504 for grey. Leaving the field empty specifies the default color." - copied from 
' http://msdn.microsoft.com/en-ca/library/windows/desktop/aa372074%28v=vs.85%29.aspx  
' See also, http://stackoverflow.com/questions/17574141/customise-fonts-with-wix-extensions and http://msdn.microsoft.com/en-us/library/windows/desktop/aa368568%28v=vs.85%29.aspx

' Windows Installer utility to execute SQL statements against an installer database
' For use with Windows Scripting Host, CScript.exe or WScript.exe
' Copyright (c) Microsoft Corporation. All rights reserved.
' Demonstrates the script-driven database queries and updates
'
Option Explicit

Const msiOpenDatabaseModeReadOnly = 0
Const msiOpenDatabaseModeTransact = 1

Dim argNum, argCount:argCount = Wscript.Arguments.Count
If (argCount < 2) Then
	Wscript.Echo "Windows Installer utility to execute SQL queries against an installer database." &_
		vbLf & " The 1st argument specifies the path to the MSI database, relative or full path" &_
		vbLf & " Subsequent arguments specify SQL queries to execute - must be in double quotes" &_
		vbLf & " SELECT queries will display the rows of the result list specified in the query" &_
		vbLf & " Binary data columns selected by a query will not be displayed" &_
		vblf &_
		vblf & "Copyright (C) Microsoft Corporation.  All rights reserved."
	Wscript.Quit 1
End If

' Scan arguments for valid SQL keyword and to determine if any update operations
Dim openMode : openMode = msiOpenDatabaseModeReadOnly
For argNum = 1 To argCount - 1
	Dim keyword : keyword = Wscript.Arguments(argNum)
	Dim keywordLen : keywordLen = InStr(1, keyword, " ", vbTextCompare)
	If (keywordLen) Then keyword = UCase(Left(keyword, keywordLen - 1))
	If InStr(1, "UPDATE INSERT DELETE CREATE ALTER DROP", keyword, vbTextCompare) Then
		openMode = msiOpenDatabaseModeTransact
	ElseIf keyword <> "SELECT" Then
		Fail "Invalid SQL statement type: " & keyword
	End If
Next

' Connect to Windows installer object
On Error Resume Next
Dim installer : Set installer = Nothing
Set installer = Wscript.CreateObject("WindowsInstaller.Installer") : CheckError

' Open database
Dim databasePath:databasePath = Wscript.Arguments(0)
Dim database : Set database = installer.OpenDatabase(databasePath, openMode) : CheckError

' Process SQL statements
Dim query, view, record, message, rowData, columnCount, delim, column
For argNum = 1 To argCount - 1
	query = Wscript.Arguments(argNum)
	Set view = database.OpenView(query) : CheckError
	view.Execute : CheckError
	If Ucase(Left(query, 6)) = "SELECT" Then
		Do
			Set record = view.Fetch
			If record Is Nothing Then Exit Do
			columnCount = record.FieldCount
			rowData = Empty
			delim = "  "
			For column = 1 To columnCount
				If column = columnCount Then delim = vbLf
				rowData = rowData & record.StringData(column) & delim
			Next
			message = message & rowData
		Loop
	End If
Next
If openMode = msiOpenDatabaseModeTransact Then database.Commit
If Not IsEmpty(message) Then Wscript.Echo message
Wscript.Quit 0

Sub CheckError
	Dim message, errRec
	If Err = 0 Then Exit Sub
	message = Err.Source & " " & Hex(Err) & ": " & Err.Description
	If Not installer Is Nothing Then
		Set errRec = installer.LastErrorRecord
		If Not errRec Is Nothing Then message = message & vbLf & errRec.FormatText
	End If
	Fail message
End Sub

Sub Fail(message)
	Wscript.Echo message
	Wscript.Quit 2
End Sub

