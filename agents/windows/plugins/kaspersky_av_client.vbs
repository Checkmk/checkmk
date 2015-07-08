' -----------------------------------------------------------------------------
' Check_MK windows agent plugin to gather information abount fullscan age and
' signature date of Kaspersky Anti-Virus software.
' -----------------------------------------------------------------------------

Option Explicit
dim strRegLoc, strStatisticsLoc, strSignDateLoc, strKasUpdateLoc, strKasFullscanLoc, strKasFullscanStateLoc, strKasRes
dim objShell, objStdOut
dim strBIASLoc, strBIAS
dim value


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
strStatisticsLoc = "HKEY_LOCAL_MACHINE\SOFTWARE\Wow6432Node\KasperskyLab\Components\34\1103\1.0.0.0\Statistics\AVState\"
strSignDateLoc = strStatisticsLoc & "Protection_BasesDate"

on error resume next
value = objShell.regread ( "HKLM\SOFTWARE\Wow6432Node\KasperskyLab\protected\AVP80\Data\LastSuccessfulFullScan" )
if err.number = 0 then
	strRegLoc = "HKLM\SOFTWARE\Wow6432Node\KasperskyLab\protected\AVP80\Data\"
else
	err.number = 0
	value = objShell.regread ( "HKLM\SOFTWARE\Wow6432Node\KasperskyLab\protected\KES8\Data\LastSuccessfulFullScan" )
	if err.number = 0 then
		strRegLoc = "HKLM\SOFTWARE\Wow6432Node\KasperskyLab\protected\KES8\Data\"
	else
		Set fso = CreateObject ("Scripting.FileSystemObject")
		Set stderr = fso.GetStandardStream (2)
		stderr.WriteLine "Kaspersky version not compatible with this plugin, check registry path."
	end if

end if

'The following registry key just contains the information when the signatures were synced from the admin server:
'strKasUpdateLoc = strRegLoc & "LastSuccessfulUpdate"
strKasFullscanLoc = strRegLoc & "LastSuccessfulFullScan"
strKasFullscanStateLoc = strRegLoc & "LastFullScanState"


strBIAS = -objShell.RegRead(strBIASLoc)
strKasRes = objShell.RegRead(strSignDateLoc)
WScript.Echo("<<<kaspersky_av_client>>>")
WScript.Echo("Signatures " & UTC2Local(Kasp2Win(strKasRes)))
strKasRes = objShell.RegRead(strKasFullscanLoc)
WScript.Echo("Fullscan " & UTC2Local(Unix2Win(strKasRes)) & " " & objShell.RegRead(strKasFullscanStateLoc))
