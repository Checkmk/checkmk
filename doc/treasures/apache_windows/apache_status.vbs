' +------------------------------------------------------------------+
' |             ____ _               _        __  __ _  __           |
' |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
' |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
' |           | |___| | | |  __/ (__|   <    | |  | | . \            |
' |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
' |                                                                  |
' | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
' +------------------------------------------------------------------+
'
' This file is part of Check_MK.
' The official homepage is at http://mathias-kettner.de/check_mk.
'
' check_mk is free software;  you can redistribute it and/or modify it
' under the  terms of the  GNU General Public License  as published by
' the Free Software Foundation in version 2.  check_mk is  distributed
' in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
' out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
' PARTICULAR PURPOSE. See the  GNU General Public License for more de-
' ails.  You should have  received  a copy of the  GNU  General Public
' License along with GNU Make; see the file  COPYING.  If  not,  write
' to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
' Boston, MA 02110-1301 USA.

'-----------------------------------------------------------------------------------------
' Check_MK-Agent-Plugin - Apache Server Status
' apache_status.vbs - check_mk agent plugin for windows
'
' Fetches the server-status page from detected or configured apache
' processes to gather status information about this apache process.
'
' To make this agent plugin work you have to load the status_module
' into your apache process. It is also needed to enable the "server-status"
' handler below the URL "/server-status".
'
' By default this plugin tries to detect all locally running apache processes
' and to monitor them. If this is not good for your environment you might
' create an apache_status.cfg file in the plugins/ directory below the path of the
' check_mk_agent and populate the servers list to prevent executing the detection mechanism.
'
' Editor : Jean-Marie DUNO <jmduno@gmail.com>, 2015-05-28 Rewrite for windows in vbs
'
' -----------------------------------------------------------------------------------------

Option Explicit
Dim proto, address, port, page, url
Dim answer, answer2, line, line2
Dim server(2)
Dim servers
Dim ssl_ports

page ="server-status?auto"

'list of https port, separate by space
ssl_ports = "443 "

Sub Pause(strPause)
     WScript.Echo (strPause)
     z = WScript.StdIn.Read(1)
End Sub

Function try_detect_servers()
	'Look for running "httpd" process with tasklist |find "httpd" to get PID
	'and then lookup port value with netstat -ano
	'Ouput an array of server with 3 parameters : Protocol address and port

	Dim objShellPID, objShellNETSTAT
	Dim CommandLine, strText, strText2
	Dim answer, cleaned
	Dim PID
	Dim objExecObject, objExecObject2
	Dim Linearray
	Dim parts
	Dim port, address, proto
	Dim server(2)
	Dim i
	'Dim servers : servers = Array()
	reDim servers(-1)

	'Look for running "httpd" process with tasklist |find "httpd" to get PID
	Set objShellPID = WScript.CreateObject("WScript.Shell")
	CommandLine = "cmd /c tasklist |find "& chr(34) &"httpd"& chr(34)
	Set objExecObject = objShellPID.Exec(CommandLine)
	strText = ""
	Do While Not objExecObject.StdOut.AtEndOfStream
		strText = strText & objExecObject.StdOut.ReadLine() & "|"
	Loop
	answer=Split(strText, "|")

	for each line in answer
		if len(Trim(line)) >0 then
				REM Output sample :
				REM ========================= ======== ================ =========== ============
				REM System Idle Process              0 Services                   0         24 K
				REM System                           4 Services                   0      2 536 K
				PID =  trim(mid(line,27,8))

				'lookup for ip and port.
				Set objShellNETSTAT = WScript.CreateObject("WScript.Shell")
				CommandLine = "cmd /c netstat -ano |find "& chr(34) & PID & chr(34)

				Set objExecObject2 = objShellNETSTAT.Exec(CommandLine)
				strText2 = ""

				Do While Not objExecObject2.StdOut.AtEndOfStream
					strText2 = strText2 & objExecObject2.StdOut.ReadLine() & "|"
				Loop
				answer2=Split(strText2, "|")

				for each line2 in answer2
					REM Output sample :
					REM Active Connections
				  REM Proto  Local Address          Foreign Address        State           PID
				  REM TCP    0.0.0.0:80             0.0.0.0:0              LISTENING       2508
				  REM TCP    [::]:80                [::]:0                 LISTENING       2508
				  REM TCP    10.10.12.103:5357      10.10.12.113:55615     TIME_WAIT       0
				  REM TCP    [eeee::aa:81e7:c4da:d732%13]:49158  [::]:0                 LISTENING       2932
				  REM TCP    [eeee::cccc:a7f7:b262:8165%28]:49158  [::]:0                 LISTENING       2932

					'removing extraspace
					Do While InStr(1, line2, "  ")
					  line2 = Replace(line2, "  ", " ")
					Loop

					'trim it and split it by space
					parts = split(trim(line2))
					if Ubound(parts) >0 then
						'get Port
						'Search from left ":" char and take the right part
						port = right(parts(1), len(parts(1)) - InStrRev( parts(1), ":" ))

						'get address
						'Search from left ":" char and take the left part
						address = left(parts(1), InStrRev( parts(1), ":" ) -1)

						if (StrComp(address, "[::]", vbTextCompare) =0) then
							address = "[::1]"
						elseIf ( StrComp(address, "0.0.0.0", vbTextCompare) = 0) then
							address = "127.0.0.1"
						End If

						'Get proto
						proto = "http"
						'Switch protocol if port is SSL port. In case you use SSL on another
						'port you would have to change/extend the ssl_port list
						if (InStr(ssl_ports, port) >0) then
							proto = "https"
						End If

						server(0) = proto
						server(1) = address
						server(2) = port

						'add the server in the servers array
						ReDim Preserve servers (UBound(servers) + 1)
						servers(UBound(servers)) = server

					End If 'Ubound(parts) >0
				next 'line2 in answer2
		end if 'len(Trim(line)) >0
	next 'line in answer

  try_detect_servers = servers
End Function 'try_detect_servers

Function ReadConfFile()
	'read the conf file and ouput an array of server with 3 parameter : Protocole address and port
	'Dim servers : servers = Array()
	reDim servers(-1)
	Dim server
	Dim Lineread
	Dim config_filename

	config_filename = Replace(WScript.ScriptFullName, WScript.ScriptName, "") & "apache_status.cfg"

	'Reading the file
	Const ForReading = 1, ForWriting = 2, ForAppending = 8
	Const TristateUseDefault = -2, TristateTrue = -1, TristateFalse = 0
	Dim fso, MyFile, TextLine

	Set fso = CreateObject("Scripting.FileSystemObject")

	If fso.FileExists(config_filename) Then
		' Open the file for input.
		Set MyFile = fso.OpenTextFile(config_filename, ForReading)

		' Read from the file and display the results.
		Do While MyFile.AtEndOfStream <> True
			TextLine = MyFile.ReadLine
			if (len(TextLine)>0 and instr(UCase(TextLine), "REM")=0 ) then
				Set server = Nothing
				server = split(TextLine, " ")
				'check the number of parameter in the line. Must be 3.
				if Ubound(server) = 2 then
					'add the server in the servers array
					ReDim Preserve servers (UBound(servers) + 1)
					servers(UBound(servers)) = server
				End If
			End If

		Loop 'MyFile.AtEndOfStream
		MyFile.Close
	Else
		Wscript.Echo "File Does not Exist"
	end If 'fso.FileExists(config_filename)

	ReadConfFile = servers
End function 'ReadConfFile

'read the conf file to get servers list
servers = ReadConfFile

'if no server from config file, try_detect_servers
if (UBound(servers)+1) = 0 Then
	servers = try_detect_servers()
end If


Wscript.Echo "<<<apache_status>>>"

for each server in servers
	proto = server(0)
	address = server(1)
	port = server(2)

	url = proto&"://"&address&":"&port&"/"&page

	On Error Resume Next
	Dim objHTTP
	Set objHTTP = CreateObject("MSXML2.XMLHTTP")
	objHTTP.open "GET", url, False
	objHTTP.send

	If Err.Number = 0 Then
		If objHTTP.Status = 200 Then
			Set line = Nothing
			Set answer = Nothing

			if (InStr(objHTTP.responseText,chr(60))>0) Then
				' if "<" inside, seems to be html output. Skip this server.
			else
				answer=Split(objHTTP.responseText, chr(10))
				for each line in answer
					if len(Trim(line)) >0 then
						Wscript.Echo address&", "&port&", "& Trim(line)
					end if
				next
			End If
		else
			Wscript.Echo "HTTP-Error ("&address&":"&port&"): "& objHTTP.Status & chr(10)' &" "& objHTTP.responseText
		End If 'objHTTP.Status = 200
	Else
		WScript.Echo "Exception ("& address &":"& port &"): " & Err.Description
		Err.Clear
	End If 'Err.Number = 0

	Set objHTTP = Nothing

next 'server in servers
