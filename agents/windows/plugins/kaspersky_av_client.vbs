' -----------------------------------------------------------------------------
' Check_MK windows agent plugin to gather information abount fullscan age and
' signature date and connection date to Kaspersky Management Server of
' Kaspersky Anti-Virus Client.
' All registry keys have values in the format: dd-MM-yyyy HH-mm-ss
'
'This script:
' 1) reads the relevant registry keys
' 2) Converts the Kaspersky date/time string to a date
' 3) Adjusts the date based on time zone bias (The offset from UTC)
' 4) Converts the date to checkmk (server-side) format: dd.MM.yyyy HH:mm:ss
' Regardless of the system's date/time settings.
' -----------------------------------------------------------------------------

Option Explicit
Const CMK_VERSION = "2.1.0p2"
dim strStatisticsLoc, strProtection_BasesDate, strProtection_LastFscan, strProtection_LastConnected
dim strBIASLoc, strBIAS
dim objShell

Set objShell = CreateObject("WScript.Shell")

' Convert the Kaspersky format (dd-MM-yyyy HH-mm-ss) to a date, by
' re-ordering the string so it's accepted as input for Date/TimeSerial.
Function Kasp2Win(KasperskyDateTime)
    Kasp2Win = DateSerial( _
                  Mid(KasperskyDateTime, 7, 4),    _
                  Mid(KasperskyDateTime, 4, 2),    _
                  Mid(KasperskyDateTime, 1, 2)) +  _
               TimeSerial( _
                  Mid(KasperskyDateTime, 12, 2),   _
                  Mid(KasperskyDateTime, 15, 2),   _
                  Mid(KasperskyDateTime, 18, 2))
End Function

' Correct the offset (positive, zero, or negative) in minutes
' from Coordinated Universal Time (UTC).
Function UTC2Local(TimeStamp)
    UTC2Local = DateAdd("n", strBIAS, CDate(TimeStamp))
End Function

' Add a leading zero for single digit values.
Function AddPrefixZero(DatePart)
    If (Len(DatePart) = 1) Then
        AddPrefixZero = "0" & DatePart
    Else
        AddPrefixZero = DatePart
    End if
End Function

' Construct a checkmk compatible datetime string:
' dd.MM.yyyy HH:mm:ss
Dim strYear, strMonth, strDay, strHour, strMinute, strSecond
Function Date2checkmk(WinDateTime)
    strYear = Year(WinDateTime)
    strMonth = AddPrefixZero(Month(WinDateTime))
    strDay = AddPrefixZero(Day(WinDateTime))
    strHour = AddPrefixZero(Hour(WinDateTime))
    strMinute = AddPrefixZero(Minute(WinDateTime))
    strSecond = AddPrefixZero(Second(WinDateTime))

    Date2checkmk = strDay & "." & strMonth & "." & strYear & " " & _
	                strHour & ":" & strMinute & ":" & strSecond
End Function

' The ActiveTimeBias determines the offset of local time
' from UTC and is a dynamic value.
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
        WScript.Echo("Signatures " & Date2checkmk(UTC2Local(Kasp2Win(strProtection_BasesDate))))
    end if

    'Protection_LastFscan key deployed empty on installation
    strProtection_LastFscan = strStatisticsLoc & "Protection_LastFscan"
    strProtection_LastFscan = objShell.RegRead(strProtection_LastFscan)
    if strProtection_LastFscan = "" OR err.number <> 0 then
        WScript.Echo("Fullscan Missing")
    else
        WScript.Echo("Fullscan " & Date2checkmk(UTC2Local(Kasp2Win(strProtection_LastFscan))))
    end if

'else
    'WScript.Echo("<<<kaspersky_av_client>>>")
    'WScript.Echo("Signatures Missing")
    'WScript.Echo("Fullscan Missing")
    'WScript.Echo("Missing Kaspersky Client")
end if
