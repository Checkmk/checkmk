' -----------------------------------------------------------------------------
' Check_MK windows agent plugin to gather information abount fullscan age and
' signature date and connection date to Kaspersky Management Server of
' Kaspersky Anti-Virus Client.
' All Keys in format dd-mm-yyyy hh-mm-ss
' -----------------------------------------------------------------------------

Option Explicit
Const CMK_VERSION = "2.0.0p21"
dim strStatisticsLoc, strProtection_BasesDate, strProtection_LastFscan, strProtection_LastConnected
dim strBIASLoc, strBIAS
dim objShell

Set objShell = CreateObject("WScript.Shell")

Function UTC2Local(TimeStamp)
   UTC2Local = DateAdd("n", strBIAS, CDate(TimeStamp))
End Function

Function Kasp2Win(TimeStamp)
  dim strTimeStampRepl
  strTimeStampRepl = Replace(TimeStamp, "-", ".", 1, 2)
  Kasp2Win = Replace(strTimeStampRepl, "-", ":")
End Function

strBIASLoc = "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\TimeZoneInformation\ActiveTimeBias"
strBIAS = -objShell.RegRead(strBIASLoc)
strStatisticsLoc = "HKEY_LOCAL_MACHINE\SOFTWARE\Wow6432Node\KasperskyLab\Components\34\1103\1.0.0.0\Statistics\AVState\"

'Protection_LastConnected key set with date of last connection to management server
strProtection_LastConnected = strStatisticsLoc & "Protection_LastConnected"
on error resume next
strProtection_LastConnected = objShell.RegRead(strProtection_LastConnected)

'If the strProtection_LastConnected key can be read Kaspersky AV is assumed to be installed
if err.number = 0 then
	WScript.Echo("<<<kaspersky_av_client>>>")

	'Protection_BasesDate key is set with old signatures from installer
	strProtection_BasesDate = strStatisticsLoc & "Protection_BasesDate"
	strProtection_BasesDate = objShell.RegRead(strProtection_BasesDate)
	if strProtection_BasesDate = "" then
		WScript.Echo("Signatures Missing")
	else
		WScript.Echo("Signatures " & UTC2Local(Kasp2Win(strProtection_BasesDate)))
	end if

	'Protection_LastFscan key deployed empty on installation
	strProtection_LastFscan = strStatisticsLoc & "Protection_LastFscan"
	strProtection_LastFscan = objShell.RegRead(strProtection_LastFscan)
	if strProtection_LastFscan = "" OR err.number <> 0 then
		WScript.Echo("Fullscan Missing")
	else
		WScript.Echo("Fullscan " & UTC2Local(Kasp2Win(strProtection_LastFscan)))
	end if

'else
	'WScript.Echo("<<<kaspersky_av_client>>>")
	'WScript.Echo("Signatures Missing")
	'WScript.Echo("Fullscan Missing")
	'WScript.Echo("Missing Kaspersky Client")
end if

